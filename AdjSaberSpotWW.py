from DmxFixture import DmxFixture


class AdjSaberSpotWW(DmxFixture):
    on = False
    brightness = 0 # expected to be between 0 and 255

    def get_dmx_message(self, hue_light_info: object) -> bytes:
        if 'on' in hue_light_info:
            self.on = hue_light_info['on']['on']

        if 'dimming' in hue_light_info:
            self.brightness = int(hue_light_info['dimming']['brightness'])
            if self.brightness > 254:
                self.brightness = 254
            if self.brightness < 0:
                self.brightness = 0

        dmx_dim_level = self.brightness if self.on else 0
        return bytes([dmx_dim_level])

    def get_state(self) -> str:
        return f"on={self.on}  brightness={self.brightness}"
