from dataclasses import dataclass
from bay_transit_agency import MuniTransitAgency
from gtfs_transit_agency import GtfsTransitAgency
from chip_ctrl import create_led_controller
from web_led_visualizer import start_web_visualizer, DEFAULT_STOP_NAMES

from gtfs_types import AgencyMetadata, FeedMetadata, Stop, Route, Trip, StopTime
from typing import Dict, Optional
from config_loader import ConfigLoader, LineConfig, StopMapping

import time
import os
import threading

@dataclass
class ControlledStop:
    stop_id: str
    led_index: int

class LineOrchestrator:
    def __init__(self, config_loader: ConfigLoader, line_name: str,
                 led_controller=None, agency=None):
        self.config_loader = config_loader
        self.line_name = line_name
        self.agency = agency

        line_config = config_loader.get_line(line_name)
        if not line_config:
            raise ValueError(f"Line '{line_name}' not found in config")

        self.route_id = line_config.route_id

        # Build controlled_stops from config
        self.controlled_stops = {}
        for stop in line_config.stops:
            self.controlled_stops[stop.stop_id] = ControlledStop(
                stop_id=stop.stop_id,
                led_index=stop.led_index
            )

        # Create or use existing LED controller
        if led_controller is None:
            controller_config = config_loader.get_led_controller(line_config.controller)
            stop_names = {
                stop.led_index: stop.stop_name
                for stop in line_config.stops
            }
            led_controller = create_led_controller(
                use_mock=controller_config.type == 'mock',
                stop_names=stop_names
            )
        self.led_controller = led_controller

        self.pulse_threshold = line_config.pulse_threshold
        self.solid_threshold = config_loader.global_config['solid_threshold']

    def get_stop_name(self, led_index: int) -> str:
        return self.config_loader.get_stop_name(self.line_name, led_index)

    def get_stop_brightness(self, led_index: int) -> int:
        return self.config_loader.get_stop_brightness(self.line_name, led_index)

    def update_leds(self):
        # Fetch real-time updates - use a larger time window to get more trips
        if not self.agency:
            raise RuntimeError("Agency not set. Cannot update LEDs without GTFS data.")
        stops = self.agency.stops(self.route_id, 7200)  # 2 hours instead of 5 minutes

        ### Default rules
        ### For each trip, if vehicle has left previous stop & is within 10 minutes of arrival, pulse the LED
        ### If the vehicle is within 30 seconds of arrival, keep the LED solid on
        ### Each trip will only have one LED on at a time. If multiple stops are within the threshold, light up closest.
        pulsing_threshold = self.pulse_threshold
        solid_on_threshold = self.solid_threshold

        pulsing = set()
        solid_on = set()
        # Print # of active trips with >1 stop within threshold
        cnt = 0
        for trip_id, stop_times in stops.items():
            if len(stop_times) > 0:
                cnt += 1
        print(f"Active trips with multiple stops within threshold: {cnt}")

        for trip_id, stop_times in stops.items():
            closest_stop = None
            min_delta = int(1e9)
            for stop_time in stop_times:
                arrival_delta = stop_time.time_to_arrival_seconds(self.agency.agency_metadata.current_time_in_timezone())
                departure_delta = stop_time.time_to_departure_seconds(self.agency.agency_metadata.current_time_in_timezone())

                # Only consider non-None deltas
                if arrival_delta is not None:
                    delta = min(min_delta, arrival_delta)
                elif departure_delta is not None:
                    delta = min(min_delta, departure_delta)
                else:
                    continue

                # Update closest stop
                if 0 <= delta < min_delta:
                    min_delta = delta
                    closest_stop = stop_time

            if closest_stop is not None and closest_stop.stop_id in self.controlled_stops:
                led_index = self.controlled_stops[closest_stop.stop_id].led_index

                if min_delta <= solid_on_threshold:
                    solid_on.add(self.controlled_stops[closest_stop.stop_id].led_index)
                elif min_delta <= pulsing_threshold:
                    pulsing.add(self.controlled_stops[closest_stop.stop_id].led_index)

            if closest_stop is not None and closest_stop.stop_id in self.controlled_stops:
                led_index = self.controlled_stops[closest_stop.stop_id].led_index
                if min_delta <= solid_on_threshold:
                    solid_on.add(led_index)
                elif min_delta <= pulsing_threshold:
                    pulsing.add(led_index)

        # If LED is both pulsing and solid on, remove from pulsing
        pulsing = pulsing - solid_on
        for stop in self.controlled_stops.values():
            if stop.led_index not in pulsing and stop.led_index not in solid_on:
                self.led_controller.set_brightness(stop.led_index, 0)  # Turn off
        # Update LED controller
        self.led_controller.set_pulsed_outputs(list(pulsing))
        for led in solid_on:
            self.led_controller.set_brightness(led, 64) # Quarter brightness

if __name__ == "__main__":
    # For testing, you can use the mock controller by setting use_mock_led=True
    import os
    use_mock = os.environ.get('USE_MOCK_LED', '').lower() in ('1', 'true', 'yes')
    print(f"USE_MOCK_LED: {use_mock}")

    # Create agency and orchestrator with config loader
    muni = MuniTransitAgency()

    orchestrator = LineOrchestrator(
        config_loader=loader,
        line_name="j_line",
        use_mock_led=use_mock,
        agency=muni
    )

    # Check if we should start the web visualizer
    use_web_visualizer = os.environ.get('USE_WEB_VISUALIZER', '').lower() in ('1', 'true', 'yes')

    if use_web_visualizer and use_mock:
        # Start web visualizer in a separate thread, sharing the same LED controller
        web_thread = threading.Thread(
            target=start_web_visualizer,
            args=(
                {stop.led_index: stop.stop_name for stop in line_config.stops},
                orchestrator.led_controller
            ),
            daemon=True
        )
        web_thread.start()
        print("Web visualizer started. Access at http://localhost:5000")
        print("Press Ctrl+C to stop the server")

    try:
        while True:
            orchestrator.update_leds()
            time.sleep(3)  # Update every 3 seconds
    except KeyboardInterrupt:
        print("Stopping orchestrator.")
        # Note: Mock controllers don't have the enabled attribute, so we don't need to set it