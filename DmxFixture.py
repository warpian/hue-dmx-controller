"""
Copyright (c) 2023 Tom Kalmijn / MIT License.
"""
class DmxFixture:
    def __init__(self, name, hue_light_id, dmx_address):
        self.name = name
        self.dmx_address = dmx_address
        self.hue_light_id = hue_light_id

    def get_dmx_message(self, hue_light_info: object) -> bytes:
        print("not implemented!")
        return bytes()

