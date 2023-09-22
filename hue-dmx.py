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

import logging
import os
import signal
import time
from typing import List

import daemon
from daemon import pidfile
from dotenv import load_dotenv

from DmxFixture import DmxFixture
from DmxSender import DmxSender
# custom classes
from HueBridge import HueBridge

# initialize variables from config file (.env)
load_dotenv()

PID_FILE = os.getenv('PID')
WORK_DIR = os.getenv('WORK_DIR')
LOG_FILE = os.getenv('LOG_FILE')
DAEMONIZE = os.getenv('DAEMONIZE', 'false').lower() == 'true'
HUE_API_KEY = os.getenv('HUE_API_KEY')
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')
STUB_DMX = os.getenv('STUB_DMX', 'false').lower() == "true"
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

def track_hue_lamps_and_update_dmx_fixtures():
    logger.info("Loading DMX fixtures")
    dmx_fixtures = load_dmx_fixtures()

    logger.info("Initializing DMX sender")
    dmx_sender = DmxSender(logger=logger)

    logger.info("Discovering Hue bulbs")
    hue_bridge = HueBridge(bridge_ip=HUE_BRIDGE_IP, api_key=HUE_API_KEY, timeout_sec=HUE_TIMEOUT_SEC, logger=logger)
    for key, value in hue_bridge.list_light_ids_and_names().items():
        logger.info(f"    {key}: {value}")

    while True:
        logger.info("Start listening for Hue bridge events...")
        for event in hue_bridge.event_stream():
            if event["type"] == "update":
                for fixture in dmx_fixtures:
                    hue_info = hue_bridge.get_light_info(fixture.hue_light_id)
                    dmx_message = fixture.get_dmx_message(hue_info)
                    if not STUB_DMX:
                        dmx_sender.send_message(fixture.dmx_address, dmx_message)
                    else:
                        logger.info(f"Update {fixture.name}")
        time.sleep(60) # try to connect again in a minute

def start():
    init_logger()
    logger.info("Starting up")
    track_hue_lamps_and_update_dmx_fixtures()

def shutdown(signum, frame):
    logger.info('Shutting down')
    exit(0)

def start_daemon():
    with daemon.DaemonContext(
            umask=0o002,
            working_directory=WORK_DIR,
            files_preserve=[file_logger.stream],
            pidfile=pidfile.PIDLockFile(PID_FILE)):
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        start()

if __name__ == "__main__":
    if DAEMONIZE:
        start_daemon()
    else:
        start()
