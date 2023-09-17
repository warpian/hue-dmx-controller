from typing import Any, Dict

from DmxFixture import DmxFixture
from ColorConverter import Converter, get_light_gamut, XYPoint


class AdjSaberSpotRGBW(DmxFixture):
    on = False
    brightness = 0 # expected to be between 0 and 255

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
        rgb = color_converter.xy_to_rgb(hue_light_info['color']['xy']['x'], hue_light_info['color']['xy']['y'])
        dmx_dim_level = self.brightness if self.on else 0
        #return bytes([rgb[0], rgb[1], rgb[2], 0])
        return bytes([0, 0, 0, 0])


    def get_state(self) -> str:
        return f"on={self.on}  brightness={self.brightness}"


    # def xy_to_rgb(self, vx, vy):
    #     vy = vy or 1e-11
    #     Y = 1
    #     X = (Y / vy) * vx
    #     Z = (Y / vy) * (1 - vx - vy)
    #
    #     # Convert to RGB using Wide RGB D65 conversion
    #     rgb = [
    #         X * 1.656492 - Y * 0.354851 - Z * 0.255038,
    #         -X * 0.707196 + Y * 1.655397 + Z * 0.036152,
    #         X * 0.051713 - Y * 0.121364 + Z * 1.011530
    #     ]
    #
    #     # Apply reverse gamma correction
    #     rgb = [(12.92 * x if x <= 0.0031308 else (1.0 + 0.055) * pow(x, 1.0 / 2.4) - 0.055) for x in rgb]
    #
    #     # Bring all negative components to zero
    #     rgb = [max(0, x) for x in rgb]
    #
    #     # If one component is greater than 1, weight components by that value
    #     max_val = max(rgb)
    #     if max_val > 1:
    #         rgb = [x / max_val for x in rgb]
    #
    #     # Round to integer RGB values between 0 and 255
    #     rgb = [round(x * 255) for x in rgb]
    #
    #     return rgb
    #
    #
    #
