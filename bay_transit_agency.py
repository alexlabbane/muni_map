import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, List
from gtfs_transit_agency import GtfsTransitAgency, Arrival
from google.transit import gtfs_realtime_pb2
from chip_ctrl import LP5018
import time
from datetime import datetime
from zoneinfo import ZoneInfo

class BayTransitAgency(GtfsTransitAgency, ABC):
    API_KEY="9204d66d-0a54-4767-b0bd-05146057d4aa"
    BASE_URL="http://api.511.org/transit/"
    
    def __init__(self):
        super().__init__()

    @classmethod
    @abstractmethod
    def lines(cls) -> Dict[str, str]:
        """Return a list of transit line IDs -> names for the given agency."""
        pass

    @property
    def name(self) -> str:
        return ""

    @property
    def id(self) -> str:
        return ""

    @property
    def stations(self) -> Dict[str, str]:
        return {}

    @property
    @abstractmethod
    def agency(self) -> str:
        pass

    @classmethod
    def BASE_URL(cls) -> str:
        return "http://api.511.org/transit/"
    
    @classmethod
    def API_KEY(cls) -> str:
        #return "9204d66d-0a54-4767-b0bd-05146057d4aa"
        return "adc7ae59-732f-4df2-b4d3-58a9cbd9cc2f"

class MuniTransitAgency(BayTransitAgency):
    def __init__(self):
        super().__init__()

    @classmethod
    def lines(cls) -> Dict[str, str]:
        # TODO: Implement line fetching logic
        return {}

    @property
    def agency(self) -> str:
        return "SF"



if __name__ == "__main__":
    lp5018 = LP5018()
    agencies = BayTransitAgency.agencies()
    print(agencies)
    muni = MuniTransitAgency()
    muni._update_realtime_feed()
    # Hack: From real-time feed, check if there is a J line train within 5 minutes of stop_id 16217 ("Right Of Way/21st St")
    # Pulse LED if arrival is within 2 minutes
    cnt = 0
    while True:
        j_stops = muni.HACK_j_stops
        print("J Line stops within 15 minutes of Right Of Way/21st St:")
        for stop in j_stops:
            print(f"Trip ID: {stop.trip_id}, Arrival: {stop.arrival_time}, Departure: {stop.departure_time}")

            arrival_parts = list(map(int, stop.arrival_time.split(":")))
            # Use America/Los_Angeles timezone in datetime.now()
            now = datetime.now(ZoneInfo("America/Los_Angeles"))
            arrival_dt = now.replace(hour=arrival_parts[0], minute=arrival_parts[1], second=arrival_parts[2])
            delta = (arrival_dt - now).total_seconds()
            if 600 <= delta <= 900:
                print("  Arrival within 15 minutes, turn on LED on output 12")
                # Set Output 12 to quarter brightness
                lp5018.set_brightness(12, 64)
                lp5018.set_brightness(13, 0)
                lp5018.set_brightness(14, 0)
                lp5018.set_brightness(15, 0)
                lp5018.set_brightness(16, 0)
            elif 300 <= delta <= 600:
                print("  Arrival within 10 minutes, turn on LED on output 13")
                # Set Output 13 to quarter brightness
                lp5018.set_brightness(12, 0)
                lp5018.set_brightness(13, 64)
                lp5018.set_brightness(14, 0)
                lp5018.set_brightness(15, 0)
                lp5018.set_brightness(16, 0)
            elif 120 <= delta <= 300:
                print("  Arrival within 5 minutes, turn on LED on output 14")
                # Set Output 14 to quarter brightness
                lp5018.set_brightness(12, 0)
                lp5018.set_brightness(13, 0)
                lp5018.set_brightness(14, 64)
                lp5018.set_brightness(15, 0)
                lp5018.set_brightness(16, 0)
            elif 30 <= delta <= 120:
                print("  Arrival within 2 minutes, turn on LED on output 15")
                # Set Output 15 to quarter brightness
                lp5018.set_brightness(12, 0)
                lp5018.set_brightness(13, 0)
                lp5018.set_brightness(15, 64)
                lp5018.set_brightness(14, 0)
                lp5018.set_brightness(16, 0)
            elif 0 <= delta < 30:
                print("  Arrival within 30 seconds, turn all LEDs on")
                # Set Output 16 to quarter brightness
                lp5018.set_brightness(12, 64)
                lp5018.set_brightness(13, 64)
                lp5018.set_brightness(16, 64)
                lp5018.set_brightness(14, 64)
                lp5018.set_brightness(15, 64)
            else:
                print("  Arrival more than 10 minutes away, turn LEDs off")
                lp5018.set_brightness(12, 0)
                lp5018.set_brightness(13, 0)
                lp5018.set_brightness(14, 0)
                lp5018.set_brightness(15, 0)
                lp5018.set_brightness(16, 0)
        
        print("\n--------------------------------\n")
        time.sleep(2)
        cnt += 1
        # only update realtime feed every 70 seconds
        if cnt % 35 == 0:
            print("Updating real-time feed...")
            muni._update_realtime_feed()