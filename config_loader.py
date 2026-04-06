"""
Configuration loader for LED mappings.

Loads stop-to-LED mappings from YAML configuration files.
Supports multiple config files and command-line specification.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path


@dataclass
class StopMapping:
    """Represents a mapping between an LED and a transit stop."""
    led_index: int
    stop_id: str
    stop_name: str
    brightness: int = 64


@dataclass
class LedControllerConfig:
    """Represents an LED controller configuration (mock or real)."""
    type: str  # 'mock' or 'lp5018'
    id: str
    num_leds: int = 24
    mock_led_id: Optional[int] = None
    lp5018: Dict[str, Any] = None


@dataclass
class LineConfig:
    """Represents a transit line configuration."""
    name: Optional[str]
    route_id: str
    controller: str  # ID of led_controllers section
    stops: List[StopMapping]
    pulse_threshold: int = 600


class ConfigLoader:
    """Load LED mapping configurations from YAML files."""

    DEFAULT_CONFIG_PATH = Path("configs/default_led_mappings.yml")

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config_data: Dict[str, Any] = {}
        self.lines: Dict[str, LineConfig] = {}
        self.led_controllers: Dict[str, LedControllerConfig] = {}
        self.global_config: Dict[str, int] = {}

    def load(self) -> Dict[str, LineConfig]:
        """Load configuration from YAML file."""
        path = self._get_config_path()

        with open(path, 'r') as f:
            self.config_data = yaml.safe_load(f)

        self._parse_global_config()
        self._parse_led_controllers()
        self._parse_lines()

        return self.lines

    def _parse_global_config(self):
        """Parse global configuration (thresholds, etc.)"""
        global_section = self.config_data.get('global', {})
        self.global_config = {
            'pulse_threshold': global_section.get('pulse_threshold', 600),
            'solid_threshold': global_section.get('solid_threshold', 30),
        }

    def _parse_led_controllers(self):
        """Parse led_controllers section - each controller is a separate node."""
        controllers_data = self.config_data.get('led_controllers', {})
        for name, config in controllers_data.items():
            self.led_controllers[name] = LedControllerConfig(
                type=config.get('type', 'mock'),
                id=config.get('id', name),
                num_leds=config.get('num_leds', 24),
                mock_led_id=config.get('mock_led_id'),
                lp5018=config.get('lp5018', {})
            )

    def _parse_lines(self):
        """Parse lines section - each line references a controller by ID."""
        lines_data = self.config_data.get('lines', {})
        if not isinstance(lines_data, dict):
            lines_data = lines_data.get('lines', {})

        for line_name, line_config in lines_data.items():
            if not isinstance(line_config, dict):
                continue

            controller_id = line_config.get('controller')
            controller_config = self.led_controllers.get(controller_id)
            if not controller_config:
                print(f"Warning: Controller '{controller_id}' not found for line '{line_name}'")
                continue

            stops = []
            for stop in line_config.get('stops', []):
                stops.append(StopMapping(
                    led_index=stop.get('led_index', 0),
                    stop_id=stop.get('stop_id', ''),
                    stop_name=stop.get('stop_name', ''),
                    brightness=stop.get('brightness', 64)
                ))

            self.lines[line_name] = LineConfig(
                name=line_config.get('name'),
                route_id=line_config.get('route_id'),
                controller=controller_id,
                stops=stops,
                pulse_threshold=line_config.get('pulse_threshold',
                    self.global_config['pulse_threshold'])
            )

    def get_line(self, line_name: str) -> Optional[LineConfig]:
        """Get line configuration by name."""
        return self.lines.get(line_name)

    def get_led_controller(self, controller_id: str) -> Optional[LedControllerConfig]:
        """Get LED controller configuration by ID."""
        return self.led_controllers.get(controller_id)

    def get_stop_name(self, line_name: str, led_index: int) -> str:
        """Get stop name for a given line and LED index."""
        line = self.lines.get(line_name)
        for stop in line.stops if line else []:
            if stop.led_index == led_index:
                return stop.stop_name
        return f"LED {led_index}"

    def get_stop_brightness(self, line_name: str, led_index: int) -> int:
        """Get stop brightness for a given line and LED index."""
        line = self.lines.get(line_name)
        for stop in line.stops if line else []:
            if stop.led_index == led_index:
                return stop.brightness
        return 64

    def _get_config_path(self) -> Path:
        """Determine the config file path."""
        if self.config_path:
            path = Path(self.config_path)
            # If no directory specified, default to configs/
            if not path.is_absolute() and not path.parent.name:
                return Path("configs") / path.name
            return path
        return self.DEFAULT_CONFIG_PATH

    @classmethod
    def find_available_configs(cls) -> List[str]:
        """Find all available YAML config files."""
        repo_path = Path(__file__).parent / "configs"
        if not repo_path.exists():
            return []
        return sorted([f.stem for f in repo_path.glob("*.yml")])

    @classmethod
    def list_available_configs(cls):
        """Print available configuration files to stdout."""
        configs = cls.find_available_configs()
        if not configs:
            print("No configuration files found.")
            return
        print("Available configurations:")
        for config in configs:
            print(f"  - {config}")
