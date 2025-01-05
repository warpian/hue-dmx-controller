"""
Copyright (c) 2023 Tom Kalmijn / MIT License.
"""
from HueModel import HueLight


class DmxFixture:
    name: str
    hue_light_id: str
    dmx_address: int
    hueLamp: HueLight

    def __init__(self, name: str, hue_light_id: str, dmx_address: int):
        self.name = name
        self.dmx_address = dmx_address
        self.hue_light_id = hue_light_id

    def get_dmx_message(self) -> bytes:
        print("not implemented!")
        return bytes()

