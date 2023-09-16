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

import daemon
import requests
from daemon import pidfile
from dotenv import load_dotenv
from pylibftdi import Device, Driver

from DmxFixture import DmxFixture
from OneChannelDimmableFixture import OneChannelDimmableFixture
from UpdateEvent import UpdateEvent

# initialize variables from config file (.env)
load_dotenv()

PID_FILE = os.getenv('PID')
WORK_DIR = os.getenv('WORK_DIR')
LOG_FILE = os.getenv('LOG_FILE')
DAEMONIZE = os.getenv('DAEMONIZE', '').lower() == 'true'
HUE_API_KEY = os.getenv('HUE_API_KEY')
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')
STUB_DMX = os.getenv('STUB_DMX')

CLIP_API_LIST_DEVICES_URL = f"https://{HUE_BRIDGE_IP}/clip/v2/resource/device"
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

pin_spot_buddha = OneChannelDimmableFixture(
    name="Buddha",
    hue_device_id="1a50407e-3634-4815-8246-dd2fba3c7cba",
    dmx_address=1)

dmx_fixtures = [pin_spot_buddha] # add more fixtures here

hue_device_list = {}

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
        logger.info(f"Updating dmx address {address}")
        dmx_data[address:address + len(data)] = data
        # address equals offset because DMX addresses start with 1 skipping the start byte in the data packet.
        with Device(ftdi_serial) as ftdi_port:
            send_dmx_packet(ftdi_port, dmx_data)
    except Exception as e:
        logger.error("Cannot send dmx packet: %s", e)


def get_hue_devices():
    headers = {
        "hue-application-key": HUE_API_KEY,
        "Connection": "keep-alive",
        "Accept": "application/json"
    }
    response = requests.get(CLIP_API_LIST_DEVICES_URL, headers=headers, verify=False)
    response.raise_for_status()
    json = response.json()
    result = {}  # map of device id to user provided name
    for device in json['data']:
        result[device['id']] = device['metadata']['name']
    return result


def hue_bridge_event_stream():
    headers = {
        "hue-application-key": HUE_API_KEY,
        "Connection": "keep-alive",
        "Accept": "text/event-stream"
    }
    with requests.get(CLIP_API_EVENT_STREAM_URL, headers=headers, stream=True, verify=False) as response:
        response.raise_for_status()
        buffer = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:
                buffer += line + "\n"
            else:
                if buffer:
                    yield buffer.strip()
                buffer = ""


def parse_sse_event(sse_event: str) -> UpdateEvent | None:
    try:
        for line in sse_event.strip().split("\n"):
            if line.startswith("data: "):
                json_str = line[len("data: "):]
                if json_str:
                    event = json.loads(json_str)[0]
                    if event["type"] == "update":
                        data = event["data"][0]
                        owner = data["owner"]
                        device_id = owner["rid"]
                        device_type = owner['rtype']
                        device_name = device_type if device_type != "device" else hue_device_list.get(device_id, "unknown")
                        return UpdateEvent(device_id, device_name, data)

    except Exception as e:
        logger.error(f"cannot parse sse event: {e}")
    return None


def track_hue_lamp_and_update_dmx():
    while True:
        try:
            for sse_event in hue_bridge_event_stream():
                event = parse_sse_event(sse_event)
                if event:
                    logger.info(f"{event.device_name} ({event.device_id.split('-')[0]})")
                    # check if dmx fixture registered for event
                    fixture: DmxFixture = next((fixture for fixture in dmx_fixtures if fixture.hue_device_id == event.device_id), None)
                    if fixture:
                        message = fixture.get_dmx_message(event.data)
                        if STUB_DMX:
                            logger.info(f"dmx update {fixture.name}: {fixture.get_state()}")
                        else:
                            update_dmx(fixture.dmx_address, message)

                    if event.device_name == "unknown":
                        logger.warn(f"received update for unknown device: {event.data}")
        except Exception as e:
            logger.error("eventstream broken: %s", e)
            time.sleep(2)

def start():
    init_logger()
    global hue_device_list
    hue_device_list = get_hue_devices()
    for key, value in hue_device_list.items():
        logger.info(f"{key.split('-')[0]}: {value}")

    logger.info("Starting up")
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
