"""
LED Visualization Module for muni_map

This module provides visualization capabilities for LED states in a software environment
when using the mock LED controller.
"""

class LEDVisualizer:
    """Simple text-based LED visualizer for software testing."""

    def __init__(self, num_leds=24):
        """Initialize the visualizer."""
        self.num_leds = num_leds
        self.led_states = [0] * num_leds  # Initialize all LEDs to off (0)

    def update_led_state(self, led_index, brightness):
        """Update the state of a specific LED."""
        if 0 <= led_index < self.num_leds:
            self.led_states[led_index] = brightness
            return True
        return False

    def update_all_leds(self, led_states):
        """Update all LED states at once."""
        if isinstance(led_states, dict):
            for led_index, brightness in led_states.items():
                self.update_led_state(led_index, brightness)
        elif isinstance(led_states, list) and len(led_states) == self.num_leds:
            self.led_states = led_states[:]
        else:
            raise ValueError("Invalid LED states format")

    def display(self, stop_names=None):
        """Display the current LED states in a simple text format."""
        print("\nLED States:")
        print("-" * 40)
        for i, brightness in enumerate(self.led_states):
            # Create a visual representation of brightness (0-255)
            if brightness == 0:
                state = "●"  # Off
            elif brightness < 64:
                state = "○"  # Dim
            elif brightness < 128:
                state = "◉"  # Medium
            elif brightness < 200:
                state = "◎"  # Bright
            else:
                state = "◉"  # Full brightness

            # Show stop name if available
            stop_name = ""
            if stop_names and isinstance(stop_names, dict):
                stop_name = stop_names.get(i, "")

            if stop_name:
                print(f"LED {i:2d} ({stop_name[:15]:15s}): {state} ({brightness:3d})")
            else:
                print(f"LED {i:2d}: {state} ({brightness:3d})")
        print("-" * 40)

    def get_led_state(self, led_index):
        """Get the brightness of a specific LED."""
        if 0 <= led_index < self.num_leds:
            return self.led_states[led_index]
        return None

    def clear(self):
        """Turn off all LEDs."""
        self.led_states = [0] * self.num_leds
        print("All LEDs cleared.")

if __name__ == "__main__":
    # Simple test of the visualizer
    visualizer = LEDVisualizer()

    # Test some LED states
    visualizer.update_led_state(0, 0)      # Off
    visualizer.update_led_state(1, 128)    # Medium
    visualizer.update_led_state(2, 255)    # Full brightness
    visualizer.update_led_state(3, 64)     # Dim

    visualizer.display()

    # Test updating all LEDs at once
    new_states = [0, 100, 200, 50, 150, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    visualizer.update_all_leds(new_states)
    visualizer.display()