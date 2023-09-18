import colorsys
from typing import Any, Dict

import kelvin_rgb
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
        (rr, gg, bb, ww) = self.rgb_to_rgbw(r, g, b)
        print(f"rgbw: {rr}, {gg}, {bb}, {ww}")
        return bytes([rr, gg, bb, ww])

    kelvin_white_led = 5000
    k_white_red = kelvin_rgb.kelvin_table[kelvin_white_led][0]
    k_white_green = kelvin_rgb.kelvin_table[kelvin_white_led][1]
    k_white_blue = kelvin_rgb.kelvin_table[kelvin_white_led][2]

    def rgb_to_rgbw(self, r, g, b):
        white_value_for_red = r * 255.0 / self.k_white_red
        white_value_for_green = g * 255.0 / self.k_white_green
        white_value_for_blue = b * 255.0 / self.k_white_blue

        white = min(white_value_for_red, white_value_for_green, white_value_for_blue)
        white = white if white <= 255 else 255

        red = int(r - white * self.k_white_red / 255)
        green = int(g - white * self.k_white_green / 255)
        blue = int(b - white * self.k_white_blue / 255)

        return red, green, blue, int(white)
