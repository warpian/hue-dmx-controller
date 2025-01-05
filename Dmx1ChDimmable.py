"""
Copyright (c) 2023 Tom Kalmijn / MIT License.
"""
import math

from DmxFixture import DmxFixture


class Dmx1ChDimmable(DmxFixture):

    def get_dmx_message(self) -> bytes:
        if not self.hueLamp.on.on:
            return bytes([0])

        dim_level = math.ceil(self.hueLamp.dimming.brightness)
        if dim_level > 255:
            dim_level = 255
        if dim_level < 0:
            dim_level = 0

        return bytes([dim_level])
