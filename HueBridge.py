"""
Copyright (c) 2023 Tom Kalmijn / MIT License.
"""
import json
import requests
from logging import Logger
from typing import Dict, Any
from urllib3.exceptions import InsecureRequestWarning

# suppress InsecureRequestWarning from urllib3
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class HueBridge:
    api_key: str
    bridge_ip: str
    timeout_sec: int
    logger: Logger
    api_url_light: str
    api_url_device: str
    api_url_events: str

    def __init__(self, bridge_ip: str, api_key: str, timeout_sec: int, logger: Logger):
        self.logger = logger
        self.api_key = api_key
        self.bridge_ip = bridge_ip
        self.timeout_sec = timeout_sec
        self.api_url_light = f"https://{bridge_ip}/clip/v2/resource/light"
        self.api_url_device = f"https://{bridge_ip}/clip/v2/resource/device"
        self.api_url_events = f"https://{bridge_ip}/eventstream/clip/v2"

    def list_light_ids_and_names(self) -> Dict[str, str]:
        headers = {
            "hue-application-key": self.api_key,
            "Accept": "application/json"
        }
        response = requests.get(self.api_url_light, headers=headers, verify=False)
        response.raise_for_status()
        json = response.json()
        result = {}  # map of device id to user provided name
        for device in json['data']:
            result[device['id']] = device['metadata']['name']
        return result

    def get_light_info(self, hue_light_id: str) -> Dict[str, Any]:
        headers = {
            "hue-application-key": self.api_key,
            "Accept": "application/json"
        }
        response = requests.get(f"{self.api_url_light}/{hue_light_id}", headers=headers, verify=False)
        response.raise_for_status()
        return response.json()['data'][0]

    def event_stream(self):
        headers = {
            "hue-application-key": self.api_key,
            "Connection": "keep-alive",
            "Accept": "text/event-stream"
        }
        with requests.get(self.api_url_events, headers=headers, stream=True, verify=False, timeout=self.timeout_sec) as response:
            response.raise_for_status()
            try:
                buffer = ""
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        buffer += line + "\n"
                    else:
                        if buffer:
                            yield self.parse_sse_event(buffer.strip())
                        buffer = ""
            except Exception as e:
                self.logger.error("Lost connection to Hue bridge: %s", e)

    def parse_sse_event(self, sse_event: str) -> Dict[str, Any] | None:
        try:
            for line in sse_event.strip().split("\n"):
                if line.startswith("data: "):
                    json_str = line[len("data: "):]
                    if json_str:
                        return json.loads(json_str)[0]
        except Exception as e:
            self.logger.error(f"Cannot parse sse event: {e}")
        return None
