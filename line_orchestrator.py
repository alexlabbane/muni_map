from dataclasses import dataclass
from bay_transit_agency import MuniTransitAgency
from gtfs_transit_agency import GtfsTransitAgency
from chip_ctrl import create_led_controller

from gtfs_types import AgencyMetadata, FeedMetadata, Stop, Route, Trip, StopTime
from typing import Dict

import time

@dataclass
class ControlledStop:
    stop_id: str
    led_index: int

class LineOrchestrator:
    def __init__(self, agency: GtfsTransitAgency, route_id: str, controlled_stops: Dict[str, ControlledStop], use_mock_led=False):
        self.agency = agency
        self.route_id = route_id
        self.controlled_stops = controlled_stops
        # Create stop names mapping for visualization
        # For demonstration, we'll use a more descriptive mapping
        # In a real implementation, this would be retrieved from GTFS data
        stop_names = {
            stop.led_index: stop.stop_id for stop in controlled_stops.values()
        }
        # Override with more descriptive names where available
        descriptive_names = {
            0: "20th St Right Of Way",
            1: "Church St & 18th St",
            3: "Church St & 16th St",
            4: "Church St & Market St",
            5: "Van Ness",
            7: "Civic Center",
            8: "Powell",
            9: "Montgomery",
            10: "Embarcadero",
            12: "Liberty St",
            13: "21st St",
            14: "22nd St",
            15: "24th St",
            17: "26th St",
            19: "28th St",
            20: "Day St",
            21: "Randall St",
            22: "30th St & Dolores St"
        }
        # Merge with the existing names to improve display
        for led_index, name in descriptive_names.items():
            if led_index in stop_names:
                stop_names[led_index] = name

        self.led_controller = create_led_controller(use_mock=use_mock_led, stop_names=stop_names)

    def update_leds(self):
        # Fetch real-time updates
        stops = self.agency.stops(self.route_id, 300)

        ### Default rules
        ### For each trip, if vehicle has left previous stop & is within 60 seconds of arrival, pulse the LED
        ### If the vehicle is <30 seconds away, keep the LED solid on
        ### Each trip will only have one LED on at a time. If multiple stops are within 30 seconds, light up closest.
        pulsing_threshold = 300  # seconds
        solid_on_threshold = 30  # seconds

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
                delta = min(
                    stop_time.time_to_arrival_seconds(self.agency.agency_metadata.current_time_in_timezone()),
                    stop_time.time_to_departure_seconds(self.agency.agency_metadata.current_time_in_timezone()))

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

            if closest_stop is not None:
                print(f"Trip {trip_id} closest stop {closest_stop.stop_id} in {min_delta} seconds")

        # If LED is both pulsing and solid on, remove from pulsing
        pulsing = pulsing - solid_on
        for stop in self.controlled_stops.values():
            if stop.led_index not in pulsing and stop.led_index not in solid_on:
                self.led_controller.set_brightness(stop.led_index, 0)  # Turn off
        # Update LED controller
        print(f"Setting pulsing LEDs: {pulsing}, solid on LEDs: {solid_on}")

        self.led_controller.set_pulsed_outputs(list(pulsing))
        for led in solid_on:
            self.led_controller.set_brightness(led, 64) # Quarter brightness

if __name__ == "__main__":
    # For testing, you can use the mock controller by setting use_mock_led=True
    use_mock = False
    if "USE_MOCK_LED" in globals() or "USE_MOCK_LED" in locals():
        use_mock = True
    else:
        import os
        use_mock = os.environ.get('USE_MOCK_LED', '').lower() in ('1', 'true', 'yes')

    muni = MuniTransitAgency()
    controlled_stops = {
        "17217": ControlledStop(stop_id="17217", led_index=10),  # Embarcadero
        "16994": ControlledStop(stop_id="16994", led_index=9),  # Montgomery
        "16995": ControlledStop(stop_id="16995", led_index=8),  # Powell
        "16997": ControlledStop(stop_id="16997", led_index=7),  # Civic Center
        "16996": ControlledStop(stop_id="16996", led_index=5),  # Van Ness
        "18059": ControlledStop(stop_id="18059", led_index=4),  # Church St & Market St
        "13984": ControlledStop(stop_id="13984", led_index=3),  # Church St & 16th St
        "13987": ControlledStop(stop_id="13987", led_index=1),  # Church St & 18th St
        "16214": ControlledStop(stop_id="16214", led_index=0),  # Right Of Way/20th St
        "16221": ControlledStop(stop_id="16221", led_index=12),  # Right Of Way/Liberty St
        "16216": ControlledStop(stop_id="16216", led_index=13),  # Right Of Way/21st St
        "16218": ControlledStop(stop_id="16218", led_index=14),  # Church St & 22nd St
        "13995": ControlledStop(stop_id="13995", led_index=15),  # Church St & 24th St
        "18156": ControlledStop(stop_id="18156", led_index=17),  # Church St & 26th St
        "18158": ControlledStop(stop_id="18158", led_index=19),  # Church St & 28th St
        "14004": ControlledStop(stop_id="14004", led_index=20),  # Church St & Day St
        "13538": ControlledStop(stop_id="13538", led_index=22),  # 30th St & Dolores St
        "16280": ControlledStop(stop_id="16280", led_index=21),  # San Jose Ave & Randall St
    }

    orchestrator = LineOrchestrator(agency=muni, route_id="J", controlled_stops=controlled_stops, use_mock_led=use_mock)
    try:
        while True:
            orchestrator.update_leds()
            time.sleep(3)  # Update every 3 seconds
    except KeyboardInterrupt:
        print("Stopping orchestrator.")
        # Note: Mock controllers don't have the enabled attribute, so we don't need to set it