from DmxFixture import DmxFixture


class OneChannelDimmableFixture(DmxFixture):
    on = False
    brightness = 0 # expected to be between 0 and 255

    def get_dmx_message(self, data) -> bytes:
        if 'on' in data:
            self.on = data['on']['on']

        if 'dimming' in data:
            self.brightness = int(data['dimming']['brightness'])
            if self.brightness > 254:
                self.brightness = 254
            if self.brightness < 0:
                self.brightness = 0

        dmx_dim_level = self.brightness if self.on else 0
        return bytes([dmx_dim_level])

    def get_state(self) -> str:
        return f"on={self.on}  brightness={self.brightness}"
