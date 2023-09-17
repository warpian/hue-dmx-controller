import os
from dotenv import load_dotenv
import requests
import json

from AdjSaberSpotWW import OneChannelDimmableFixture
from UpdateEvent import UpdateEvent

load_dotenv()

# Suppress only the single InsecureRequestWarning from urllib3
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

HUE_API_KEY = os.getenv('HUE_API_KEY')
HUE_LAMP_ID = os.getenv('HUE_LAMP_ID')
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')

DMX_ADDRESS = int(os.getenv('DMX_ADDRESS'))

DEVICES_URL = f"https://{HUE_BRIDGE_IP}/clip/v2/resource/device"
EVENT_STREAM_URL = f"https://{HUE_BRIDGE_IP}/eventstream/clip/v2"

buddha_fixture = OneChannelDimmableFixture(
    name="Buddha",
    hue_device_id="1a50407e-3634-4815-8246-dd2fba3c7cba",
    dmx_address=1)

HUE_ID_PIXAR = "e6c587a3-f25e-47a5-9807-a60029187af4"

dmx_fixtures = [buddha_fixture]

def get_hue_devices():
    headers = {
        "hue-application-key": HUE_API_KEY,
        "Connection": "keep-alive",
        "Accept": "application/json"
    }
    response = requests.get(DEVICES_URL, headers=headers, verify=False)
    response.raise_for_status()
    json = response.json()
    result = {}  # map of device id to user provided name
    for device in json['data']:
        result[device['id']] = device['metadata']['name']
    return result


device_list = get_hue_devices()
print(device_list)


def event_stream(url):
    headers = {
        "hue-application-key": HUE_API_KEY,
        "Connection": "keep-alive",
        "Accept": "text/event-stream"
    }
    with requests.get(url, headers=headers, stream=True, verify=False) as response:
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
                        device_name = device_type if device_type != "device" else device_list.get(device_id, "unknown")
                        return UpdateEvent(device_id, device_name, data)

    except Exception as e:
        print(f"cannot parse sse event: {e}")
    return None

for sse_event in event_stream(EVENT_STREAM_URL):
    event = parse_sse_event(sse_event)
    if event:
        print(f"{event.device_name} ({event.device_id.split('-')[0]})")
        # check if fixture registered for this event
        fixture = next((fixture for fixture in dmx_fixtures if fixture.hue_device_id == event.device_id), None)
        if fixture:
            dmx_message = fixture.get_dmx_message(event.data)
            # dmx_update(fixture)

        if event.device_name == "unknown":
            print(event.data)
