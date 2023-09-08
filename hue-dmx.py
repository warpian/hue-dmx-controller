import logging
import os
import time
import json
import daemon
from daemon import pidfile
from dotenv import load_dotenv
import requests

load_dotenv()

def track_hue_lamp_and_update_dmx(log_file):
    logger = logging.getLogger('hue-dmx')
    logger.setLevel(logging.INFO)

    log_file_handler = logging.FileHandler(log_file)
    log_file_handler.setLevel(logging.INFO)

    format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format_string)

    log_file_handler.setFormatter(formatter)
    logger.addHandler(log_file_handler)

    hue_api_key = os.getenv('HUE_API_KEY')
    hue_lamp_id = os.getenv('HUE_LAMP_ID')
    hue_bridge_ip = os.getenv('HUE_BRIDGE_IP')

    while True:
        response = requests.get(f"http://{hue_bridge_ip}/api/{hue_api_key}/lights/{hue_lamp_id}")
        if response.status_code == 200:
            response_obj = json.loads(response.text)
            if response_obj['state']['on']:
                logger.info("Spot On")
            else:
                logger.info("Spot Off")
        time.sleep(5)


def start_daemon():
    with daemon.DaemonContext(
             working_directory=os.getenv('WORK_DIR'),
             umask=0o002,
             pidfile=pidfile.TimeoutPIDLockFile(os.getenv('PID')),
    ):
        track_hue_lamp_and_update_dmx(os.getenv('LOG_FILE'))


if __name__ == "__main__":
    # start_daemon()
    track_hue_lamp_and_update_dmx(os.getenv('LOG_FILE'))
