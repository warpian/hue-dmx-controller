# MIT License
#
# Copyright (c) 2023 Tom Kalmijn
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import json
import logging
import os
import threading
from typing import List, Dict

import time
from dotenv import load_dotenv

from DmxFixture import DmxFixture
from DmxSender import DmxSender
from HueBridge import HueBridge
from HueModel import On, Color, Dimming

RUNNING_AS_SERVICE = os.getenv('RUNNING_AS_SERVICE')

# initialize variables from config file (.env)
script_dir = os.path.dirname(os.path.abspath(__file__))

if RUNNING_AS_SERVICE:
    dotenv_path = os.path.join(script_dir, 'config-service.env')
else:
    dotenv_path = os.path.join(script_dir, 'config-console.env')

load_dotenv(dotenv_path=dotenv_path)

PID_FILE = os.getenv('PID')
WORK_DIR = os.getenv('WORK_DIR')
LOG_FILE = os.getenv('LOG_FILE')
HUE_API_KEY = os.getenv('HUE_API_KEY')
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')
STUB_DMX = os.getenv('STUB_DMX', 'false').lower() == 'true'
HUE_TIMEOUT_SEC = int(os.environ.get('HUE_TIMEOUT_SEC', 240))

logger = logging.getLogger()
file_logger = logging.FileHandler(LOG_FILE)


def init_logger():
    global logger, file_logger
    logger.setLevel(logging.INFO)
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.INFO)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_logger)
    logger.addHandler(console_logger)


def load_dmx_fixtures() -> List[DmxFixture]:
    result: List[DmxFixture] = []
    try:
        i = 1
        while True:
            name: str = os.getenv(f"FIXTURE{i}_NAME")
            hue_id: str = os.getenv(f"FIXTURE{i}_HUE_ID")
            dmx_address: int = int(os.getenv(f"FIXTURE{i}_DMX_ADDRESS", "0"))
            class_name: str = os.getenv(f"FIXTURE{i}_CLASS")
            if name and hue_id and dmx_address and class_name:
                logger.info(f"    {name}: dmx_address={dmx_address}, hue_id={hue_id}")
                module = __import__(class_name)
                dmx_fixture_sub_class = getattr(module, class_name)
                fixture = dmx_fixture_sub_class(name, hue_id, dmx_address)
                result.append(fixture)
                i += 1
            else:
                break
    except Exception as e:
        logger.error(f"Error loading DMX fixtures: {e}")
    return result


# Changes the Hue 'function' metadata field of your first mapped DMX fixture (.env). The 'function' field is carefully
# chosen not to influence the fixture's behavior. Changing 'function' is inconsequential. The value being set
# alternates between 'mixed' and 'unknown'. These are both valid values according to the Hue API v2.
#
# The change of the fixture will trigger an 'update' event that comes back to our script via the http event stream.
# Scheduling this method every 2 minutes prevents the event stream from timing out.
def send_bridge_heart_beat(hue_bridge):
    stop_event = threading.Event()
    while not stop_event.is_set():
        try:
            hue_id = os.getenv(f"FIXTURE1_HUE_ID")
            hue_light = hue_bridge.get_light(hue_id)
            function = "unknown" if hue_light.metadata.function == "mixed" else "mixed"
            hue_bridge.set_light_state(hue_id, {"metadata": {"function": function}})
        except Exception as e:
            logger.error("Error sending heart beat to Hue Bridge: %s", e)
        time.sleep(180)


def track_hue_lamps_and_update_dmx_fixtures():
    logger.info("Loading DMX fixtures")
    dmx_fixtures = load_dmx_fixtures()

    logger.info("Initializing DMX sender")
    dmx_sender = DmxSender(logger=logger)

    hue_bridge = HueBridge(bridge_ip=HUE_BRIDGE_IP, api_key=HUE_API_KEY, timeout_sec=HUE_TIMEOUT_SEC, logger=logger)
    hue_bulbs = hue_bridge.list_light_ids_and_names()

    # get initial state of dmx fixtures
    for fixture in dmx_fixtures:
        if fixture.hue_light_id in hue_bulbs:
            fixture.hueLamp = hue_bridge.get_light(fixture.hue_light_id)
        else:
            logger.error(f"Hue id for fixture '{fixture.name}' cannot be found.")
            logger.info("Valid id's:")
            for key, value in hue_bulbs.items():
                logger.info(f"    {key}: {value}")
            exit(1)

    threading.Thread(target=send_bridge_heart_beat, args=(hue_bridge,), daemon=True).start()

    while True:
        logger.info("Start listening for Hue bridge events...")
        for event in hue_bridge.event_stream():
            if event["type"] == "update":
                # logger.info(json.dumps(event, indent=4))
                updates: Dict[str, {}] = {obj["id"]: obj for obj in event.get("data", []) if "id" in obj} # map of hue_id -> update
                changed_hue_ids =  list(updates.keys())
                try:
                    for fixture in (f for f in dmx_fixtures if f.hue_light_id in changed_hue_ids):
                        update = updates.get(fixture.hue_light_id)

                        if "on" in update:
                            fixture.hueLamp.on = On.model_validate(update["on"])
                        if "color" in update:
                            fixture.hueLamp.color.xy = Color.model_validate(update["color"]).xy
                        if "dimming" in update:
                            fixture.hueLamp.dimming = Dimming.model_validate(update["dimming"])

                        dmx_message = fixture.get_dmx_message()
                        if STUB_DMX:
                            logger.info(f"Update {fixture.name}")
                        else:
                            dmx_sender.send_message(fixture.dmx_address, dmx_message)
                except Exception as e:
                    logger.error("Error updating fixture: %s", e)
        time.sleep(60)  # try to connect again in a minute


def shutdown(signum, frame):
    logger.info('Shutting down')
    exit(0)


if __name__ == "__main__":
    init_logger()
    if RUNNING_AS_SERVICE:
        logger.info("Starting Hue DMX service")
    else:
        logger.info("Running Hue DMX")
    track_hue_lamps_and_update_dmx_fixtures()
