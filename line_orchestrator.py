from dataclasses import dataclass
from bay_transit_agency import MuniTransitAgency
from gtfs_transit_agency import GtfsTransitAgency
from chip_ctrl import LP5018

from gtfs_types import AgencyMetadata, FeedMetadata, Stop, Route, Trip, StopTime
from typing import Dict

import time

@dataclass
class ControlledStop:
    stop_id: str
    led_index: int

class LineOrchestrator:
    def __init__(self, agency: GtfsTransitAgency, route_id: str, controlled_stops: Dict[str, ControlledStop]):
        self.agency = agency
        self.route_id = route_id
        self.controlled_stops = controlled_stops
        self.led_controller = LP5018()

    def update_leds(self):
        # Fetch real-time updates
        stops = self.agency.stops(self.route_id, 60)

        ### Default rules
        ### For each trip, if vehicle has left previous stop & is within 60 seconds of arrival, pulse the LED
        ### If the vehicle is <30 seconds away, keep the LED solid on
        ### Each trip will only have one LED on at a time. If multiple stops are within 30 seconds, light up closest.
        pulsing_threshold = 60  # seconds
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
    chip = LP5018()
    muni = MuniTransitAgency()
    controlled_stops = {
        "17217": ControlledStop(stop_id="17217", led_index=12),  # Embarcadero
        "18059": ControlledStop(stop_id="18059", led_index=13),  # Church & Market
        "16216": ControlledStop(stop_id="16216", led_index=14),  # Right Of Way/21st St
        "14004": ControlledStop(stop_id="14004", led_index=15),  # Church St & Day St
        "15418": ControlledStop(stop_id="15418", led_index=16),  # Balboa Park BART
    }

    orchestrator = LineOrchestrator(agency=muni, route_id="J", controlled_stops=controlled_stops)
    try:
        while True:
            orchestrator.update_leds()
            time.sleep(3)  # Update every 3 seconds
    except KeyboardInterrupt:
        print("Stopping orchestrator.")
        chip.enabled = False