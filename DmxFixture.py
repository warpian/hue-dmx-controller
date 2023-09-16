class DmxFixture:
    def __init__(self, name, hue_device_id, dmx_address):
        self.name = name
        self.dmx_address = dmx_address
        self.hue_device_id = hue_device_id

    def get_dmx_message(self, data) -> bytes:
        print("not implemented!")
        return bytes()

    def get_state(self) -> str:
        return f"get_state not implemented for fixture {self.name} ({self.dmx_address})"
