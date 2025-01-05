import json
import logging
import os
import threading
from typing import List, Optional, Set

import time
from dotenv import load_dotenv

from DmxFixture import DmxFixture
from DmxSender import DmxSender
from HueBridge import HueBridge


class DmxController:
    DEBOUNCE_DELAY = 0.2 # 200 milliseconds debounce delay

    def __init__(self):
        self.logger = self._init_logger()
        self.dmx_fixtures: List[DmxFixture] = []
        self.dmx_sender: Optional[DmxSender] = None
        self.hue_bridge: Optional[HueBridge] = None
        self.running_as_service = os.getenv('RUNNING_AS_SERVICE', 'false').lower() == 'true'

        self.pending_updates: Set[str] = set()
        self.update_lock = threading.Lock()
        self.debounce_timer = None
        self._load_env()
        self._initialize()

    @staticmethod
    def _init_logger():
        """
        Initializes and returns the logger.
        """
        logger = logging.getLogger("DmxController")
        logger.setLevel(logging.INFO)
        log_file = os.getenv('LOG_FILE', 'dmx_controller.log')

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        return logger

    def _load_env(self):
        """
        Loads environment variables from the appropriate `.env` file.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dotenv_path = os.path.join(script_dir, 'config-service.env' if self.running_as_service else 'config-console.env')
        load_dotenv(dotenv_path=dotenv_path)

    def _initialize(self):
        """
        Initializes DMX fixtures, DMX sender, and the Hue bridge connection.
        """
        self.logger.info("Loading DMX fixtures")
        self.dmx_fixtures = self._load_dmx_fixtures()

        self.logger.info("Initializing DMX sender")
        self.dmx_sender = DmxSender(logger=self.logger)

        self.logger.info("Connecting to Hue bridge")
        self.hue_bridge = HueBridge(
            bridge_ip=os.getenv('HUE_BRIDGE_IP'),
            api_key=os.getenv('HUE_API_KEY'),
            timeout_sec=int(os.getenv('HUE_TIMEOUT_SEC', 240)),
            logger=self.logger
        )

        self._validate_fixtures()

    def _load_dmx_fixtures(self) -> List[DmxFixture]:
        """
        Loads and returns a list of DMX fixtures from environment variables.
        """
        result = []
        try:
            i = 1
            while True:
                name = os.getenv(f"FIXTURE{i}_NAME")
                hue_id = os.getenv(f"FIXTURE{i}_HUE_ID")
                dmx_address = int(os.getenv(f"FIXTURE{i}_DMX_ADDRESS", "0"))
                class_name = os.getenv(f"FIXTURE{i}_CLASS")
                if name and hue_id and dmx_address and class_name:
                    self.logger.info(f"    {name}: dmx_address={dmx_address}, hue_id={hue_id}")
                    module = __import__(class_name)
                    dmx_fixture_sub_class = getattr(module, class_name)
                    fixture = dmx_fixture_sub_class(name, hue_id, dmx_address)
                    result.append(fixture)
                    i += 1
                else:
                    break
        except Exception as e:
            self.logger.error(f"Error loading DMX fixtures: {e}")
        return result

    def _validate_fixtures(self):
        """
        Validates that all DMX fixtures are mapped to existing Hue lights.
        """
        hue_bulbs = self.hue_bridge.list_light_ids_and_names()
        for fixture in self.dmx_fixtures:
            if fixture.hue_light_id not in hue_bulbs:
                self.logger.error(f"Hue ID for fixture '{fixture.name}' cannot be found.")
                self.logger.info("Valid IDs:")
                for key, value in hue_bulbs.items():
                    self.logger.info(f"    {key}: {value}")
                exit(1)

    def send_heartbeat(self):
        """
        Sends periodic updates to the Hue bridge to prevent timeouts.
        """
        def heartbeat():
            while True:
                try:
                    hue_id = os.getenv("FIXTURE1_HUE_ID")
                    hue_light = self.hue_bridge.get_light(hue_id)
                    function = "unknown" if hue_light.metadata.function == "mixed" else "mixed"
                    self.hue_bridge.set_light_state(hue_id, {"metadata": {"function": function}})
                except Exception as e:
                    self.logger.error("Error sending heartbeat to Hue bridge: %s", e)
                time.sleep(180)  # Every 3 minutes

        threading.Thread(target=heartbeat, daemon=True).start()

    @staticmethod
    def _contains_button_short_release(event: dict) -> bool:
        if "data" not in event:
            return False

        for item in event["data"]:
            if item.get("type") == "button":
                button = item.get("button", {})
                if button.get("last_event") == "short_release":
                    return True
        return False

    def track_and_update_fixtures(self):
        """
        Listens for Hue bridge events and synchronizes updates with DMX fixtures.
        """
        self.logger.info("Start listening for Hue bridge events...")
        while True:
            for event in self.hue_bridge.event_stream():
                if event["type"] == "update":
                    self.logger.info(json.dumps(event, indent=4))

                    if self._contains_button_short_release(event):
                        changed_hue_ids = [fixture.hue_light_id for fixture in self.dmx_fixtures]
                    else:
                        changed_hue_ids = [obj["id"] for obj in event.get("data", []) if "id" in obj]
                    self._schedule_updates(changed_hue_ids)
            time.sleep(60)  # Retry connection every minute if disconnected

    def _schedule_updates(self, changed_hue_ids: List[str]):
        """
        Adds the given Hue light IDs to the pending updates set and schedules debounced processing.
        """
        with self.update_lock:
            self.pending_updates.update(changed_hue_ids)
            if self.debounce_timer is None:
                self.debounce_timer = threading.Timer(self.DEBOUNCE_DELAY, self._debounced_process_updates)
                self.debounce_timer.start()

    def _debounced_process_updates(self):
        """
        Processes the pending updates after the debounce delay.
        """
        with self.update_lock:
            self.debounce_timer = None
            changed_hue_ids = list(self.pending_updates)
            self.pending_updates.clear()

        self._process_updates(changed_hue_ids)

    def _process_updates(self, changed_hue_ids: List[str]):
        """
        Updates DMX fixtures for the given list of Hue light IDs.
        """
        try:
            for fixture in (f for f in self.dmx_fixtures if f.hue_light_id in changed_hue_ids):
                fixture.hueLamp = self.hue_bridge.get_light(fixture.hue_light_id)
                dmx_message = fixture.get_dmx_message()
                if os.getenv('STUB_DMX', 'false').lower() == 'true':
                    self.logger.info(f"Update {fixture.name}")
                else:
                    self.dmx_sender.send_message(fixture.dmx_address, dmx_message)
        except Exception as e:
            self.logger.error("Error updating fixture: %s", e)


if __name__ == "__main__":
    controller = DmxController()
    controller.send_heartbeat()
    controller.track_and_update_fixtures()
