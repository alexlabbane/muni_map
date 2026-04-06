"""
muni_map Architecture Assistant Skill

This skill helps users understand the architecture of the muni_map repository,
which is a Python-based transit data processing system for Bay Area transit systems.

Usage: /muni_map_architecture

Key features:
- Explains the system's architecture and component relationships
- Describes how transit data is processed and displayed
- Provides usage examples and extension guidelines
"""

def get_architecture_overview():
    """Provide an overview of the muni_map architecture."""
    return """
# muni_map Architecture Overview

## Core Components

The muni_map system is a Python-based transit data processing system designed for Bay Area transit systems, particularly San Francisco Muni.

### 1. Data Model Layer (gtfs_types.py)
- AgencyMetadata: Contains agency information including timezone
- Stop: Represents transit stops with geographic coordinates
- Route: Represents transit routes
- Trip: Represents scheduled trips
- StopTime: Represents arrival/departure times at specific stops
- FeedMetadata: Contains information about the GTFS feed itself

### 2. Abstract Base Classes (gtfs_transit_agency.py)
- GtfsTransitAgency: Abstract base class providing common functionality:
  - GTFS data loading and parsing
  - Real-time data feed processing (GTFS-realtime)
  - Time calculations for arrivals/departures
  - API request handling

### 3. Bay Area Specific Implementation (bay_transit_agency.py)
- BayTransitAgency: Abstract base class for Bay Area transit agencies
- MuniTransitAgency: Concrete implementation for San Francisco Muni

### 4. Hardware Control (chip_ctrl.py)
- LP5018: Class for controlling LP5018 LED driver via I2C
  - Provides methods for setting LED brightness
  - Supports pulsing LEDs for visual notification

### 5. Line Orchestrator (line_orchestrator.py)
- LineOrchestrator: Main class that ties everything together
  - Coordinates between transit data and hardware control
  - Implements logic for when and how to light LEDs based on arrival times
"""

def get_system_flow():
    """Describe the system flow."""
    return """
## System Flow

1. **Initialization**:
   - Create transit agency instance (e.g., MuniTransitAgency)
   - Load static GTFS data from datafeeds/SF/
   - Initialize hardware controller (LP5018)

2. **Data Processing**:
   - Fetch real-time GTFS data from 511.org API
   - Parse and update stop times with real-time information
   - Calculate time to arrival/departure for stops

3. **Hardware Control**:
   - Determine which stops have upcoming arrivals
   - Map stops to physical LEDs
   - Set LED states based on time thresholds:
     - < 30 seconds: Solid on (quarter brightness)
     - 30-300 seconds: Pulsing
     - > 300 seconds: Off

4. **Continuous Operation**:
   - Periodic updates (every 3 seconds)
   - Real-time data refreshing (every 30 seconds)
   - LED state updates based on current transit information
"""

def get_usage_examples():
    """Provide usage examples."""
    return """
## Usage Examples

### Basic Usage
```python
from bay_transit_agency import MuniTransitAgency

# Create agency instance
muni = MuniTransitAgency()

# Get upcoming stops for a route (e.g., J line)
stops = muni.stops("J", 3600)  # Get stops within 1 hour
```

### Hardware Control Usage (Config-Based)
```python
from line_orchestrator import LineOrchestrator, ControlledStop
from bay_transit_agency import MuniTransitAgency
from config_loader import ConfigLoader

# Load configuration from YAML file
loader = ConfigLoader("configs/j_line.yml")
loader.load()

# Create orchestrator with config loader
muni = MuniTransitAgency()
orchestrator = LineOrchestrator(
    config_loader=loader,
    line_name="j_line",
    agency=muni
)

# Update LEDs (this is done in a loop in the main script)
orchestrator.update_leds()
```

## Key Features

- GTFS Data Support: Full parsing of standard GTFS files
- Real-time Integration: Real-time feed processing from 511.org
- Hardware Integration: Control of LED displays via I2C
- Time-based Logic: Smart LED behavior based on arrival times
- Extensible Design: Modular architecture that can be extended for other agencies
"""

def get_extension_guidelines():
    """Provide guidelines for extending the system."""
    return """
## Extension Guidelines

### Adding New Transit Agencies
1. Create new class inheriting from BayTransitAgency
2. Implement required abstract methods
3. Configure appropriate API endpoints and keys

### Extending Hardware Control
1. Create new classes for different LED drivers
2. Add new patterns for LED behavior
3. Support for multiple LED arrays

### Improving Data Processing
1. Better time handling with timezone support
2. Add caching mechanisms
3. Enhanced error handling for API failures
4. Add logging for debugging

### Adding New Features
1. Mobile/Web interface
2. Notification system (email/SMS)
3. Data export capabilities
4. Analytics and reporting features
"""

def main():
    """Main function to display the architecture information."""
    print("muni_map Architecture Assistant")
    print("=" * 40)
    print(get_architecture_overview())
    print(get_system_flow())
    print(get_usage_examples())
    print(get_extension_guidelines())

if __name__ == "__main__":
    main()