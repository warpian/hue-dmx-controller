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

ftdi_serial_port = ''

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
hue_connection_lost = False

def init_logger():
    global logger, file_logger
    logger.setLevel(logging.INFO)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_logger)


def init_ftdi_driver():
    try:
        driver = Driver()
        devices = driver.list_devices()
        for device in devices:
            manufacturer, description, serial = device
            logger.info(f"Manufacturer: {manufacturer}, Description: {description}, Serial: {serial}")
            global ftdi_serial_port
            ftdi_serial_port = serial
    except Exception as e:
        logger.error("Cannot initialize FTDI serial port: %s", e)
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
        ftdi_port.flush()
#        ftdi_port.close()
    except Exception as e:
        logger.error("Cannot send dmx packet: %s", e)


def update_dmx(address: int, data: bytes):
    try:
        logger.info(f"Updating dmx address {address}")
        dmx_data[address:address + len(data)] = data
        # address equals offset because DMX addresses start with 1 skipping the start byte in the data packet.
        with Device(ftdi_serial_port) as ftdi_port:
            send_dmx_packet(ftdi_port, dmx_data)
    except Exception as e:
        logger.error("Cannot send dmx packet: %s", e)


def track_hue_lamp_and_update_dmx():
    global brightness, hue_connection_lost

    while True:
        try:
            response = requests.get(f"http://{HUE_BRIDGE_IP}/api/{HUE_API_KEY}/lights/{HUE_LAMP_ID}")
            if response.status_code == 200:
                hue_connection_lost = False
                response_obj = json.loads(response.text)
                new_brightness = response_obj['state']['bri'] if response_obj['state']['on'] else 0
                if brightness != new_brightness: # only update dmx when dim level changes (fixture should 'HOLD' last DMX setting)
                    brightness = new_brightness
                    data = bytearray([brightness])  # just updates one DMX channel at address 1
                    update_dmx(DMX_ADDRESS, bytes(data))
            time.sleep(HUE_POLL_SECONDS)
        except Exception as e:
            if not hue_connection_lost:
                logger.error("Cannot contact Hue Bridge: %s", e)
            hue_connection_lost = True
            time.sleep(5)


def start():
    init_logger()
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
