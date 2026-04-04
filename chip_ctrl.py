import smbus2
import threading
import time

from typing import List

class LP5018:
    """Class to interface with the LP5018 LED driver via I2C."""

    # LP5018 I2C address
    DEFAULT_I2C_ADDRESS = 0x28

    # Register addresses
    REG_DEVICE_CONFIG0 = 0x00
    REG_DEVICE_CONFIG1 = 0x01
    REG_LED_CONFIG0 = 0x02
    REG_BANK_BRIGHTNESS = 0x03
    REG_BANK_A_COLOR = 0x04
    REG_BANK_B_COLOR = 0x05
    REG_BANK_C_COLOR = 0x06
    # LED 0-7 Brightness
    REG_LED0_BRIGHTNESS = 0x07
    REG_LED1_BRIGHTNESS = 0x08
    REG_LED2_BRIGHTNESS = 0x09
    REG_LED3_BRIGHTNESS = 0x0A
    REG_LED4_BRIGHTNESS = 0x0B
    REG_LED5_BRIGHTNESS = 0x0C
    REG_LED6_BRIGHTNESS = 0x0D
    REG_LED7_BRIGHTNESS = 0x0E
    # OUT0_COLOR - OUT23_COLOR
    REG_OUT0_COLOR = 0x0F
    REG_OUT1_COLOR = 0x10
    REG_OUT2_COLOR = 0x11
    REG_OUT3_COLOR = 0x12
    REG_OUT4_COLOR = 0x13
    REG_OUT5_COLOR = 0x14
    REG_OUT6_COLOR = 0x15
    REG_OUT7_COLOR = 0x16
    REG_OUT8_COLOR = 0x17
    REG_OUT9_COLOR = 0x18
    REG_OUT10_COLOR = 0x19
    REG_OUT11_COLOR = 0x1A
    REG_OUT12_COLOR = 0x1B
    REG_OUT13_COLOR = 0x1C
    REG_OUT14_COLOR = 0x1D
    REG_OUT15_COLOR = 0x1E
    REG_OUT16_COLOR = 0x1F
    REG_OUT17_COLOR = 0x20
    REG_OUT18_COLOR = 0x21
    REG_OUT19_COLOR = 0x22
    REG_OUT20_COLOR = 0x23
    REG_OUT21_COLOR = 0x24
    REG_OUT22_COLOR = 0x25
    REG_OUT23_COLOR = 0x26

    DEFAULT_CONFIG = {
        REG_DEVICE_CONFIG0: 0x40,
        REG_DEVICE_CONFIG1: 0x3C,
        REG_LED_CONFIG0: 0x00,
        REG_LED0_BRIGHTNESS: 0xFF,
        REG_LED1_BRIGHTNESS: 0xFF,
        REG_LED2_BRIGHTNESS: 0xFF,
        REG_LED3_BRIGHTNESS: 0xFF,
        REG_LED4_BRIGHTNESS: 0xFF,
        REG_LED5_BRIGHTNESS: 0xFF,
        REG_LED6_BRIGHTNESS: 0xFF,
        REG_LED7_BRIGHTNESS: 0xFF,
        REG_OUT0_COLOR: 0x00,
        REG_OUT1_COLOR: 0x00,
        REG_OUT2_COLOR: 0x00,
        REG_OUT3_COLOR: 0x00,
        REG_OUT4_COLOR: 0x00,
        REG_OUT5_COLOR: 0x00,
        REG_OUT6_COLOR: 0x00,
        REG_OUT7_COLOR: 0x00,
        REG_OUT8_COLOR: 0x00,
        REG_OUT9_COLOR: 0x00,
        REG_OUT10_COLOR: 0x00,
        REG_OUT11_COLOR: 0x00,
        REG_OUT12_COLOR: 0x00,
        REG_OUT13_COLOR: 0x00,
        REG_OUT14_COLOR: 0x00,
        REG_OUT15_COLOR: 0x00,
        REG_OUT16_COLOR: 0x00,
        REG_OUT17_COLOR: 0x00,
        REG_OUT18_COLOR: 0x00,
        REG_OUT19_COLOR: 0x00,
        REG_OUT20_COLOR: 0x00,
        REG_OUT21_COLOR: 0x00,
        REG_OUT22_COLOR: 0x00,
        REG_OUT23_COLOR: 0x00,
    }

    def __init__(self, bus_number=1, i2c_address=DEFAULT_I2C_ADDRESS):
        """Initialize the I2C bus."""
        self.bus = smbus2.SMBus(bus_number)
        self.i2c_address = i2c_address

        # Set default config
        self.pulsing_outputs = set()
        self.reset()

        # For pulsing outputs
        self.enabled = True
        self.pulse_thread = threading.Thread(target=self._pulse_thread_fn, args=(self,))
        self.pulse_thread.start()

    # def __del__(self):
    #     """Cleanup on deletion."""
    #     self.enabled = False
    #     if self.pulse_thread and self.pulse_thread.is_alive():
    #         self.pulse_thread.join()
    #     self.bus.close()

    def reset(self):
        """Reset the LP5018 to default configuration."""
        self.pulsing_outputs.clear()
        for reg, value in self.DEFAULT_CONFIG.items():
            self._write_register(reg, value)

    def set_brightness(self, output: int, brightness: int):
        """Set the brightness of a specific output (0-23)."""
        self.pulsing_outputs.discard(output)
        self._set_brightness(output, brightness)

    def set_pulsed_outputs(self, outputs: List[int]):
        """Set multiple outputs to pulse."""
        for output in outputs:
            if not (0 <= output <= 23):
                raise ValueError("Output must be between 0 and 23.")
        
        self.pulsing_outputs = set(outputs)

    def pulse_output(self, output: int):
        """Start pulsing a specific output (0-23)."""
        if not (0 <= output <= 23):
            raise ValueError("Output must be between 0 and 23.")

        self.pulsing_outputs.add(output)

    # Private methods
    def _read_register(self, register):
        """Read a byte from a specific register."""
        return self.bus.read_byte_data(self.i2c_address, register)

    def _write_register(self, register, value):
        """Write a byte to a specific register."""
        self.bus.write_byte_data(self.i2c_address, register, value)

    def _set_brightness(self, output: int, brightness: int):
        """Set the brightness of a specific output (0-23)."""
        if not (0 <= output <= 23):
            raise ValueError("Output must be between 0 and 23.")
        if not (0 <= brightness <= 255):
            raise ValueError("Brightness must be between 0 and 255.")

        reg = self.REG_OUT0_COLOR + output
        self._write_register(reg, brightness)

    @staticmethod
    def _pulse_thread_fn(chip: 'LP5018'):
        """Smoothly pulse the LEDs in chip.pulsing_outputs"""
        while chip.enabled:
            if len(chip.pulsing_outputs) == 0:
                # Nothing to pulse, just wait
                # print("No outputs to pulse, sleeping...")
                time.sleep(0.5)
                continue

            for step in range(256):
                pulsing_outputs = list(chip.pulsing_outputs)
                for output in pulsing_outputs:
                    brightness = abs(255 - step * 2) if step < 128 else abs(step * 2 - 255)
                    # print(f"Setting output {output} to brightness {brightness}")
                    chip._set_brightness(output, brightness)
                time.sleep(0.01)

if __name__ == "__main__":
    lp5018 = LP5018()
    time.sleep(2)

    # Turn on each LED in sequence
    for output in range(24):
        print(f"Setting output {output} to 32 brightness")
        lp5018.set_brightness(output, 32)
        time.sleep(1)

    # # Set Output 12-17 to full brightness
    # for output in range(12, 18):
    #     lp5018.set_brightness(output, 255)

    # time.sleep(2)
    # # Smoothly pulse outputs 12-17 indefinitely; offset each LED evenly by 0.5 seconds
    # # e.g., when LED 12 is at max brightness, LED 13 is at half brightness, LED 14 is at min brightness, etc.
    # print("Pulsing outputs 12-17. Press Ctrl+C to stop.")
    # try:
    #     lp5018.set_pulsed_outputs([12, 13, 14, 15, 16, 17])
    #     # while True:
    #     #     for step in range(256):
    #     #         for i, output in enumerate(range(12, 18)):
    #     #             # Calculate brightness with phase offset
    #     #             phase = (step + (i * 42)) % 256
    #     #             brightness = abs(255 - phase * 2) if phase < 128 else abs(phase * 2 - 255)
    #     #             lp5018.set_brightness(output, brightness // 4) # Quarter brightness
    #     #         time.sleep(0.01)
    # except KeyboardInterrupt:
    #     print("Stopping pulsing.")