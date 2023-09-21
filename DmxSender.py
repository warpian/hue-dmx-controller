"""
Copyright (c) 2023 Tom Kalmijn / MIT License.
"""
import time
from logging import Logger

from pylibftdi import Device, Driver

class DmxSender:

    ftdi_serial: str = None
    dmx_data = bytearray(513)
    # 513: one start byte (0x00) plus 512 bytes of channel data
    # dmx_data is automatically filled with zeros, incidentally also correctly setting the start byte.
    # According to DMX512, when sending a message to a fixture, we need to repeat the untouched DMX
    # channels. For this reason channel data is buffered in dmx_data.

    def __init__(self, logger: Logger):
        self.logger = logger
        self.init_ftdi_driver()

    def init_ftdi_driver(self):
        try:
            driver = Driver()
            devices = driver.list_devices()
            for device in devices:
                manufacturer, description, serial = device
                if manufacturer == "FTDI":
                    self.logger.info(f"Found FTDI port with serial {serial}")
                    self.ftdi_serial = serial
                    break
        except Exception as e:
            self.logger.error("Cannot determine FTDI serial: %s", e)
            raise e

    def send_message(self, address: int, data: bytes):
        assert self.ftdi_serial is not None, "FTDI driver is not initialized"
        try:
            self.dmx_data[address:address + len(data)] = data
            # address equals offset because DMX addresses start with 1 skipping the start byte in the data packet.
            with Device(self.ftdi_serial) as ftdi_port:
                self.send_dmx_packet(ftdi_port, self.dmx_data)
        except Exception as e:
            self.logger.error("Cannot send dmx packet: %s", e)

    def send_dmx_packet(self, ftdi_port: Device, data: bytes):
        try:
            # reset dmx channel
            ftdi_port.ftdi_fn.ftdi_set_bitmode(1, 0x01)  # set break
            ftdi_port.write(b'\x00')
            time.sleep(0.001)
            ftdi_port.write(b'\x01')
            ftdi_port.ftdi_fn.ftdi_set_bitmode(0, 0x00)  # release break
            ftdi_port.flush()

            ftdi_port.ftdi_fn.ftdi_set_line_property(8, 2, 0)
            ftdi_port.baudrate = 250000
            ftdi_port.write(bytes(data))
        except Exception as e:
            self.logger.error("Cannot send dmx packet: %s", e)
