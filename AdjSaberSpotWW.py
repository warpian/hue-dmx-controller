"""
Copyright (c) 2023 Tom Kalmijn / MIT License.
"""
import math
from typing import Dict, Any

from DmxFixture import DmxFixture


class AdjSaberSpotWW(DmxFixture):

    def get_dmx_message(self, hue_light_info: Dict[str, Any]) -> bytes:
        if not 'on' in hue_light_info or not hue_light_info['on']['on']:
            return bytes([0])

        dim_level = math.ceil(hue_light_info['dimming']['brightness']) if 'dimming' in hue_light_info else 255
        if dim_level > 255:
            dim_level = 255
        if dim_level < 0:
            dim_level = 0

        return bytes([dim_level])
