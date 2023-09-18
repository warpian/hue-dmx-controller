import math
from typing import Any, Dict

import numpy as np

from ColorConverter import Converter, XYPoint
from DmxFixture import DmxFixture


class AdjSaberSpotRGBW(DmxFixture):
    on = False
    brightness = 0  # expected to be between 0 and 255

    def get_dmx_message(self, hue_light_info: Dict[str, Any]) -> bytes:
        if 'on' in hue_light_info:
            self.on = hue_light_info['on']['on']

        if 'dimming' in hue_light_info:
            self.brightness = int(hue_light_info['dimming']['brightness'])
            if self.brightness > 254:
                self.brightness = 254
            if self.brightness < 0:
                self.brightness = 0

        gamut = (
            XYPoint(hue_light_info['color']['gamut']['red']['x'], hue_light_info['color']['gamut']['red']['y']),
            XYPoint(hue_light_info['color']['gamut']['green']['x'], hue_light_info['color']['gamut']['green']['y']),
            XYPoint(hue_light_info['color']['gamut']['blue']['x'], hue_light_info['color']['gamut']['blue']['y']),
        )
        color_converter = Converter(gamut)
        (r, g, b) = color_converter.xy_to_rgb(hue_light_info['color']['xy']['x'], hue_light_info['color']['xy']['y'])
        print(f"rgb: {r}, {g}, {b}")
        (h, s, i) = self.rgb_to_hsi(r, b, g)
        print(f"hsi: {h}, {s}, {i}")
        return bytes([h, s, i])

    def rgb_to_hsi(self, red: int, green: int, blue: int):
        with np.errstate(divide='ignore', invalid='ignore'):
            intensity = np.divide(blue + green + red, 3)

            minimum = np.minimum(np.minimum(red, green), blue)
            saturation = 1 - 3 * np.divide(minimum, red + green + blue)

            sqrt_calc = np.sqrt(((red - green) * (red - green)) + ((red - blue) * (green - blue)))

            if green >= blue:
                hue = np.arccos((1/2 * ((red-green) + (red - blue)) / sqrt_calc))
            else:
                hue = 2 * math.pi - np.arccos((1/2 * ((red-green) + (red - blue)) / sqrt_calc))

            hue = hue * 180 / math.pi
            hue = (hue + 45) % 360

            print(f"hsi raw: {hue}, {saturation}, {intensity}")

            h_byte = self.byteval((hue / 360) * 255)
            s_byte = self.byteval((1 - saturation) * 255)
            i_byte = self.byteval(intensity)
            return h_byte, s_byte, i_byte

    def byteval(self, num: float) -> int:
        result = num
        if result < 0:
            result = 0
        if result > 255:
            result = 255
        return int(result)
