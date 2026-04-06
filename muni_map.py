#!/usr/bin/env python3
"""
Muni Map - Main entrypoint for the transit LED visualization system.
"""

import argparse
import sys
import threading
from pathlib import Path

# Add repo path
repo_path = Path(__file__).parent
if str(repo_path) not in sys.path:
    sys.path.insert(0, str(repo_path))

from bay_transit_agency import MuniTransitAgency
from line_orchestrator import LineOrchestrator
from web_led_visualizer import start_web_visualizer
from config_loader import ConfigLoader


def main():
    """Main entry point for muni_map."""
    parser = argparse.ArgumentParser(
        description="Muni Map - LED visualization for transit arrivals"
    )
    parser.add_argument("--config", "-c", type=str, help="YAML config file")
    parser.add_argument("--list-configs", action="store_true", help="List available configs")
    parser.add_argument("--line", "-l", type=str, help="Line name to run")
    parser.add_argument("--web-visualizer", action="store_true", help="Start web visualizer")
    parser.add_argument("--port", type=int, default=5000, help="Web visualizer port")

    args = parser.parse_args()

    # List available configs
    if args.list_configs:
        for c in ConfigLoader.find_available_configs():
            print(c)
        return 0

    # Load config
    loader = ConfigLoader(args.config)
    lines = loader.load()

    # Validate line selection
    if not args.line:
        print("Available lines:")
        for name, line_config in lines.items():
            print(f"  - {line_config.name or name} (route: {line_config.route_id})")
        print("\nUse --line <name> to specify which line to run")
        return 1

    if args.line not in lines:
        print(f"Error: Line '{args.line}' not found")
        print("Available lines:")
        for name in lines.keys():
            print(f"  - {name}")
        return 1

    # Create agency and orchestrator
    muni = MuniTransitAgency()
    orchestrator = LineOrchestrator(
        config_loader=loader,
        line_name=args.line,
        agency=muni
    )

    # Start web visualizer if requested
    if args.web_visualizer:
        stop_names = {
            stop.led_index: stop.stop_name
            for stop in loader.get_line(args.line).stops
        }
        web_thread = threading.Thread(
            target=start_web_visualizer,
            args=(stop_names, orchestrator.led_controller),
            daemon=True
        )
        web_thread.start()
        print(f"Web visualizer: http://localhost:{args.port}")

    print(f"Running: {args.line} (route: {orchestrator.route_id})")
    print(f"Controlled stops: {len(orchestrator.controlled_stops)}")

    import time
    try:
        while True:
            orchestrator.update_leds()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nStopped")


if __name__ == "__main__":
    main()
