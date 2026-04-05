import smbus2
import threading
import time
import os

from typing import List

# Import LED visualizer for mock mode
try:
    from led_visualization import LEDVisualizer
except ImportError:
    # If the visualizer isn't available, create a dummy class
    class LEDVisualizer:
        def __init__(self, num_leds=24):
            self.num_leds = num_leds
            self.led_states = [0] * num_leds

        def update_all_leds(self, led_states):
            # Dummy implementation
            pass

        def display(self):
            # Dummy implementation
            pass

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


class MockLP5018:
    """Mock class for LP5018 LED driver that simulates hardware behavior without actual I2C communication."""

    def __init__(self, bus_number=1, i2c_address=0x28, stop_names=None):
        """Initialize the mock LED driver."""
        self.bus_number = bus_number
        self.i2c_address = i2c_address
        self.pulsing_outputs = set()
        self.led_states = {}
        self._initialize_led_states()

        # Store stop names mapping if provided
        self.stop_names = stop_names or {}

        # Create LED visualizer for display
        self.visualizer = LEDVisualizer()

        # Simulate the LED states in memory
        print(f"MockLP5018 initialized. Bus: {bus_number}, Address: {i2c_address}")

    def _initialize_led_states(self):
        """Initialize all LED states to 0 (off)."""
        for i in range(24):
            self.led_states[i] = 0

    def reset(self):
        """Reset the mock LED driver to default configuration."""
        self.pulsing_outputs.clear()
        self._initialize_led_states()
        print("MockLP5018 reset called")
        # Update visualizer after reset
        self.visualizer.update_all_leds(self.led_states)
        self.visualizer.display(self.stop_names)

    def set_brightness(self, output: int, brightness: int):
        """Set the brightness of a specific output (0-23) - mock version."""
        if not (0 <= output <= 23):
            raise ValueError("Output must be between 0 and 23.")
        if not (0 <= brightness <= 255):
            raise ValueError("Brightness must be between 0 and 255.")

        self.pulsing_outputs.discard(output)
        self.led_states[output] = brightness
        print(f"MockLP5018: Setting output {output} to brightness {brightness}")
        # Update visualizer with new state
        self.visualizer.update_led_state(output, brightness)
        self.visualizer.display(self.stop_names)

    def set_pulsed_outputs(self, outputs: List[int]):
        """Set multiple outputs to pulse - mock version."""
        for output in outputs:
            if not (0 <= output <= 23):
                raise ValueError("Output must be between 0 and 23.")

        self.pulsing_outputs = set(outputs)
        print(f"MockLP5018: Setting pulsed outputs to {outputs}")
        # Update visualizer with current states
        self.visualizer.update_all_leds(self.led_states)
        self.visualizer.display(self.stop_names)

    def pulse_output(self, output: int):
        """Start pulsing a specific output (0-23) - mock version."""
        if not (0 <= output <= 23):
            raise ValueError("Output must be between 0 and 23.")

        self.pulsing_outputs.add(output)
        print(f"MockLP5018: Starting to pulse output {output}")
        # Update visualizer with current states
        self.visualizer.update_all_leds(self.led_states)
        self.visualizer.display(self.stop_names)

    def get_led_state(self, output: int) -> int:
        """Get the current brightness of a specific LED output."""
        return self.led_states.get(output, 0)

    def get_all_led_states(self) -> dict:
        """Get all LED states."""
        return self.led_states.copy()

    def clear_pulsing_outputs(self):
        """Clear all pulsing outputs."""
        self.pulsing_outputs.clear()


def create_led_controller(bus_number=1, i2c_address=0x28, use_mock=False, stop_names=None):
    """
    Factory function to create either a real or mock LED controller.

    Args:
        bus_number: I2C bus number
        i2c_address: I2C address of the device
        use_mock: If True, return a MockLP5018 instance; otherwise return LP5018 instance
        stop_names: Dictionary mapping LED indices to stop names for visualization

    Returns:
        LP5018 or MockLP5018 instance
    """
    # Check environment variable for mock mode
    if use_mock or os.environ.get('USE_MOCK_LED', '').lower() in ('1', 'true', 'yes'):
        return MockLP5018(bus_number, i2c_address, stop_names)
    else:
        return LP5018(bus_number, i2c_address)


if __name__ == "__main__":
    # Test the mock functionality
    print("Testing LED controller creation...")

    # Test with mock
    mock_controller = create_led_controller(use_mock=True)
    print(f"Created controller type: {type(mock_controller).__name__}")

    # Test setting brightness
    mock_controller.set_brightness(5, 128)
    mock_controller.set_brightness(10, 200)
    mock_controller.set_pulsed_outputs([1, 2, 3])

    # Test with real
    try:
        real_controller = create_led_controller(use_mock=False)
        print(f"Created controller type: {type(real_controller).__name__}")
    except Exception as e:
        print(f"Could not create real controller (expected in mock test): {e}")

    print("Test completed.")