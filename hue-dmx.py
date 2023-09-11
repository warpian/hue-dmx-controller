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

# initialize variables from config file (.env)
load_dotenv()

PID_FILE = os.getenv('PID')
WORK_DIR = os.getenv('WORK_DIR')
LOG_FILE = os.getenv('LOG_FILE')
DAEMONIZE = os.getenv('DAEMONIZE', '').lower() == 'true'

HUE_API_KEY = os.getenv('HUE_API_KEY')
HUE_LAMP_ID = os.getenv('HUE_LAMP_ID')
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')
HUE_POLL_SECONDS = float(os.getenv('HUE_POLL_SEC'))

DMX_ADDRESS = int(os.getenv('DMX_ADDRESS'))

brightness = -1
# brightness: the last dimming level is cached for optimization. DMX data is sent only when there is a change
# on the side of the Philips Hue bulb. This assumes that your DMX fixtures have a feature to HOLD the last setting
# (instead of blacking out). If your fixture does not have this option or you want to turn off your DMX fixtures
# when the script exits, then you need to add code to keep sending the DMX data (e.g. 44 times per second).

dmx_data = bytearray(513)
# 513: one start byte (0x00) plus 512 bytes of channel data
# dmx_data is automatically filled with zeros, incidentally also correctly setting the start byte.
# According to DMX512, when sending a message to a fixture, we need to repeat the untouched DMX
# channels. For this reason channel data is buffered in dmx_data.

logger = logging.getLogger()
file_logger = logging.FileHandler(LOG_FILE)


def init_logger():
    global logger, file_logger
    logger.setLevel(logging.INFO)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_logger)


def track_hue_lamp_and_update_dmx():
    logger.info("Starting Hue-DMX Daemon...")
    global brightness

    while True:
        response = requests.get(f"http://{HUE_BRIDGE_IP}/api/{HUE_API_KEY}/lights/{HUE_LAMP_ID}")
        if response.status_code == 200:
            response_obj = json.loads(response.text)
            new_brightness = response_obj['state']['bri'] if response_obj['state']['on'] else 0
            if brightness != new_brightness:
                brightness = new_brightness
                data = bytearray([brightness])  # specific to my situation, updates one DMX channel at address 1
                update_dmx(DMX_ADDRESS, bytes(data))
        time.sleep(HUE_POLL_SECONDS)


def send_dmx_packet(device: Device, data: bytes):
    # reset dmx channel
    device.ftdi_fn.ftdi_set_bitmode(1, 0x01)  # set break
    device.write(b'\x00')
    time.sleep(0.001)
    device.write(b'\x01')
    device.ftdi_fn.ftdi_set_bitmode(0, 0x00)  # release break
    device.flush()

    device.ftdi_fn.ftdi_set_line_property(8, 2, 0)
    device.baudrate = 250000
    device.write(bytes(data))
    device.flush()
    device.close()


def update_dmx(address: int, data: bytes):
    global dmx_data
    driver = Driver()
    devices = driver.list_devices()

    if not devices:
        logger.error("No FTDI devices found.")
        return

    for device in devices:
        manufacturer, description, serial = device
        logger.debug(f"Manufacturer: {manufacturer}, Description: {description}, Serial: {serial}")

        with Device(serial) as dev:
            logger.info(f"Updating dmx address {address}")
            dmx_data[address:address + len(data)] = data
            # address equals offset because DMX addresses start with 1 skipping the start byte in the data packet.
            send_dmx_packet(dev, dmx_data)


def shutdown(signum, frame):
    logger.info('shutting down')
    exit(0)


def start_daemon():
    with daemon.DaemonContext(
            umask=0o002,
            working_directory=WORK_DIR,
            files_preserve=[file_logger.stream],
            pidfile=pidfile.PIDLockFile(PID_FILE)):
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        init_logger()
        track_hue_lamp_and_update_dmx()


if __name__ == "__main__":
    if DAEMONIZE:
        start_daemon()
    else:
        init_logger()
        track_hue_lamp_and_update_dmx()


