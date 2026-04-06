#!/usr/bin/env python3
"""
Interactive muni_map architecture explorer
"""

import sys
import os

# Add the repository path to Python path
repo_path = "/home/alexlabbane/repos/muni_map"
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

def show_menu():
    """Display interactive menu."""
    print("\n" + "="*50)
    print("muni_map Architecture Explorer")
    print("="*50)
    print("1. System Overview")
    print("2. Component Details")
    print("3. System Flow")
    print("4. Usage Examples")
    print("5. Extension Guidelines")
    print("6. Exit")
    print("="*50)

def main():
    """Main interactive loop."""
    while True:
        show_menu()
        choice = input("Select an option (1-6): ").strip()

        if choice == "1":
            print("\n" + "="*50)
            print("SYSTEM OVERVIEW")
            print("="*50)
            print("""
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
            """)

        elif choice == "2":
            print("\n" + "="*50)
            print("COMPONENT DETAILS")
            print("="*50)
            print("""
## Component Details

### 1. gtfs_types.py
This file defines the core data structures used throughout the system:
- Dataclasses for all GTFS entities
- Time calculation methods for arrival/departure times
- Timezone handling with zoneinfo

### 2. gtfs_transit_agency.py
The base class that implements common GTFS functionality:
- Data loading from GTFS files
- Real-time feed processing
- API request handling with error management
- Time-based calculations with proper timezone handling

### 3. bay_transit_agency.py
Agency-specific implementation for Bay Area transit:
- MuniTransitAgency implementation
- API key management
- Route and agency-specific methods
- Base URL configuration for 511.org

### 4. chip_ctrl.py
Hardware control layer for LED displays:
- I2C communication with LP5018 chip
- Brightness control for individual LEDs
- Pulsing functionality for visual notifications
- Thread-safe LED state management

### 5. line_orchestrator.py
The main orchestration layer:
- Maps transit stops to physical LEDs
- Implements LED behavior logic based on arrival times
- Coordinates between transit data and hardware control
- Provides the main execution loop for continuous updates
            """)

        elif choice == "3":
            print("\n" + "="*50)
            print("SYSTEM FLOW")
            print("="*50)
            print("""
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
            """)

        elif choice == "4":
            print("\n" + "="*50)
            print("USAGE EXAMPLES")
            print("="*50)
            print("""
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
            """)

        elif choice == "5":
            print("\n" + "="*50)
            print("EXTENSION GUIDELINES")
            print("="*50)
            print("""
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
            """)

        elif choice == "6":
            print("Thank you for exploring the muni_map architecture!")
            break

        else:
            print("Invalid choice. Please select 1-6.")

if __name__ == "__main__":
    main()