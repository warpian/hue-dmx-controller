import logging
import os
import time
import json
import daemon
from pylibftdi import Device, Driver
from daemon import pidfile
from dotenv import load_dotenv
import requests

load_dotenv()
logger = logging.getLogger('hue-dmx')
logger.setLevel(logging.INFO)

log_file_handler = logging.FileHandler(os.getenv('LOG_FILE'))
log_file_handler.setLevel(logging.INFO)

format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(format_string)

log_file_handler.setFormatter(formatter)
logger.addHandler(log_file_handler)

dmx_brightness = -1

def track_hue_lamp_and_update_dmx():
    global dmx_brightness
    hue_api_key = os.getenv('HUE_API_KEY')
    hue_lamp_id = os.getenv('HUE_LAMP_ID')
    hue_bridge_ip = os.getenv('HUE_BRIDGE_IP')

    while True:
        response = requests.get(f"http://{hue_bridge_ip}/api/{hue_api_key}/lights/{hue_lamp_id}")
        if response.status_code == 200:
            response_obj = json.loads(response.text)
            dmx_brightness = response_obj['state']['bri'] if response_obj['state']['on'] else 0
            syncDmx()
        time.sleep(0.5)


def syncDmx():
    driver = Driver()
    devices = driver.list_devices()

    if not devices:
        logger.error("No FTDI devices found")
        return

    data = bytearray(513)
    data[0] = 0
    data[1] = dmx_brightness

    for device in devices:
        manufacturer, description, serial = device
        logger.debug(f"Manufacturer: {manufacturer}, Description: {description}, Serial: {serial}")

        with Device(serial) as dev:
            dev.ftdi_fn.ftdi_set_bitmode(1, 0x01) # set break
            dev.write(b'\x00')
            time.sleep(0.001)
            dev.write(b'\x01')
            dev.ftdi_fn.ftdi_set_bitmode(0, 0x00) # release break
            dev.flush()

            dev.ftdi_fn.ftdi_set_line_property(8, 2, 0)
            dev.baudrate = 250000
            dev.write(bytes(data))
            dev.close()


def start_daemon():
    with daemon.DaemonContext(
             working_directory=os.getenv('WORK_DIR'),
             umask=0o002,
             pidfile=pidfile.TimeoutPIDLockFile(os.getenv('PID')),
    ):
        track_hue_lamp_and_update_dmx()


if __name__ == "__main__":
    #start_daemon()
    track_hue_lamp_and_update_dmx()
