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
import signal
import time
from typing import Dict, Any, List

import daemon
import requests
from daemon import pidfile
from dotenv import load_dotenv
from pylibftdi import Device, Driver

from AdjSaberSpotRGBW import AdjSaberSpotRGBW
from AdjSaberSpotWW import AdjSaberSpotWW
from DmxFixture import DmxFixture

# initialize variables from config file (.env)
load_dotenv()

PID_FILE = os.getenv('PID')
WORK_DIR = os.getenv('WORK_DIR')
LOG_FILE = os.getenv('LOG_FILE')
DAEMONIZE = os.getenv('DAEMONIZE', '').lower() == 'true'
HUE_API_KEY = os.getenv('HUE_API_KEY')
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')
STUB_DMX = os.getenv('STUB_DMX')
HUE_TIMEOUT_SEC = os.environ.get('HUE_TIMEOUT_SEC', 240)

CLIP_API_RESOURCE_LIGHT = f"https://{HUE_BRIDGE_IP}/clip/v2/resource/light"
CLIP_API_RESOURCE_DEVICE = f"https://{HUE_BRIDGE_IP}/clip/v2/resource/device"
CLIP_API_EVENT_STREAM_URL = f"https://{HUE_BRIDGE_IP}/eventstream/clip/v2"

ftdi_serial = ''

dmx_data = bytearray(513)
# 513: one start byte (0x00) plus 512 bytes of channel data
# dmx_data is automatically filled with zeros, incidentally also correctly setting the start byte.
# According to DMX512, when sending a message to a fixture, we need to repeat the untouched DMX
# channels. For this reason channel data is buffered in dmx_data.

# Suppress only the single InsecureRequestWarning from urllib3
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger()
file_logger = logging.FileHandler(LOG_FILE)
hue_connection_lost = False

pin_spot_buddha = AdjSaberSpotWW(name="Buddha", hue_device_id="0ff176d1-21c0-4497-b491-65c53a4214bd",
                                            dmx_address=1)

pin_spot_bureau = AdjSaberSpotRGBW(name="Bureau", hue_device_id="e0a5dd4a-67d3-4f40-ab6d-67c8ebbd463d",
                                   dmx_address=2)
dmx_fixtures: List[DmxFixture] = [pin_spot_buddha, pin_spot_bureau]  # add more fixtures here


def init_logger():
    global logger, file_logger
    logger.setLevel(logging.INFO)
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.INFO)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_logger)
    logger.addHandler(console_logger)


def init_ftdi_driver():
    try:
        driver = Driver()
        devices = driver.list_devices()
        for device in devices:
            manufacturer, description, serial = device
            if manufacturer == "FTDI":
                logger.info(f"Found FTDI port with serial {serial}")
                global ftdi_serial
                ftdi_serial = serial
                break
    except Exception as e:
        logger.error("Cannot determine FTDI serial: %s", e)
        raise e


def send_dmx_packet(ftdi_port: Device, data: bytes):
    try:
        # reset dmx channel
        ftdi_port.ftdi_fn.ftdi_set_bitmode(1, 0x01)  # set break
        ftdi_port.write(b'\x00')
        time.sleep(0.001)
        ftdi_port.write(b'\x01')
        ftdi_port.ftdi_fn.ftdi_set_bitmode(0, 0x00)  # release break
        ftdi_port.flush()

        ftdi_port.ftdi_fn.ftdi_set_line_property(8, 2, 0)
        ftdi_port.baudrate = 250000
        ftdi_port.write(bytes(data))
    except Exception as e:
        logger.error("Cannot send dmx packet: %s", e)


def update_dmx(address: int, data: bytes):
    try:
        dmx_data[address:address + len(data)] = data
        # address equals offset because DMX addresses start with 1 skipping the start byte in the data packet.
        with Device(ftdi_serial) as ftdi_port:
            send_dmx_packet(ftdi_port, dmx_data)
    except Exception as e:
        logger.error("Cannot send dmx packet: %s", e)


def get_hue_lights() -> Dict[str, str]:
    headers = {
        "hue-application-key": HUE_API_KEY,
        "Accept": "application/json"
    }
    response = requests.get(CLIP_API_RESOURCE_LIGHT, headers=headers, verify=False)
    response.raise_for_status()
    json = response.json()
    result = {}  # map of device id to user provided name
    for device in json['data']:
        result[device['id']] = device['metadata']['name']
    return result


def get_hue_light_info(hue_device_id: str) -> Dict[str, Any]:
    headers = {
        "hue-application-key": HUE_API_KEY,
        "Accept": "application/json"
    }
    response = requests.get(f"{CLIP_API_RESOURCE_LIGHT}/{hue_device_id}", headers=headers, verify=False)
    response.raise_for_status()
    return response.json()['data'][0]


def hue_bridge_event_stream():
    headers = {
        "hue-application-key": HUE_API_KEY,
        "Connection": "keep-alive",
        "Accept": "text/event-stream"
    }
    with requests.get(CLIP_API_EVENT_STREAM_URL, headers=headers, stream=True, verify=False, timeout=HUE_TIMEOUT_SEC) as response:
        logger.info("Connecting to Hue bridge...")
        response.raise_for_status()
        try:
            buffer = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    buffer += line + "\n"
                else:
                    if buffer:
                        yield buffer.strip()
                    buffer = ""
        except Exception as e:
            logger.error("Lost connection to Hue bridge: %s", e)


def parse_sse_event(sse_event: str) -> Dict[str, Any] | None:
    try:
        for line in sse_event.strip().split("\n"):
            if line.startswith("data: "):
                json_str = line[len("data: "):]
                if json_str:
                    return json.loads(json_str)[0]
    except Exception as e:
        logger.error(f"Cannot parse sse event: {e}")
    return None


def track_hue_lamp_and_update_dmx():
    while True:
        for sse_event in hue_bridge_event_stream():
            event = parse_sse_event(sse_event)
            if event and event["type"] == "update":
                for fixture in dmx_fixtures:
                    info = get_hue_light_info(fixture.hue_device_id)
                    if STUB_DMX:
                        fixture.get_dmx_message(info)
                        #logger.info(f"Update {fixture.name}")
                    else:
                        #logger.info(f"Update {fixture.name}")
                        update_dmx(fixture.dmx_address, fixture.get_dmx_message(info))
        time.sleep(5)



def start():
    init_logger()
    logger.info("Starting up")
    logger.info("discovering Hue lights...")
    for key, value in get_hue_lights().items():
         logger.info(f"{key}: {value}")
    init_ftdi_driver()
    track_hue_lamp_and_update_dmx()


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
