from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List
import requests
import json
import os
import time
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

from google.transit import gtfs_realtime_pb2

from gtfs_types import AgencyMetadata, FeedMetadata, Stop, Route, Trip, StopTime

@dataclass
class Arrival:
    station_id: str
    arrival_time: time.struct_time
    is_at_station: bool

"""Abstract base class for GTFS transit lines. Currently supports only bay area transit via 511.org, but can be refactored to support other regions."""
class GtfsTransitAgency(ABC):
    
    def __init__(self):
        # Initialize data structures to hold static GTFS data for the agency
        self.agency_metadata: AgencyMetadata = None
        self.feed_metadata: FeedMetadata = None
        self.stops : Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self.trips: Dict[str, Trip] = {}
        # For now, don't use calendar.txt and calendar_dates.txt

        self._read_datafeed()
        self._update_realtime_feed()

    # Public Interface

    def estimated_arrivals(self) -> List[Arrival]:
        pass

    def estimated_arrivals(self, station_id: str) -> List[Arrival]:
        pass

    def update_datafeed(self):
        """GTFS datafeed download allows the user to download a zip file containing GTFS dataset for the
            specified operator/agency or the regional feed."""
        res = self._send_api_request(
            request_url=f"{self.BASE_URL()}datafeeds",
            params={"api_key": self.API_KEY(), "Operator_id": self.agency}
        )
        # Save URL res.content bytes to zip file on disk in datafeeds/agency subdirectory, then unzip for parsing
        # Create datafeeds/agency directory if it doesn't exist
        os.makedirs(f"datafeeds/{self.agency}", exist_ok=True)
        with open(f"datafeeds/{self.agency}/datafeed.zip", "wb") as f:
            f.write(res.content)

        # Unzip files to disk
        with zipfile.ZipFile(f"datafeeds/{self.agency}/datafeed.zip", 'r') as zip_ref:
            zip_ref.extractall(f"datafeeds/{self.agency}/")

    @classmethod
    def agencies(cls) -> Dict[str, str]:
        """URL request to get operator list from API."""
        res = cls._send_api_request_json(
            request_url=f"{cls.BASE_URL()}gtfsoperators",
            params={"api_key": cls.API_KEY(), "format": "json"}
        )

        return {agency["Id"]: agency["Name"] for agency in res}

    @classmethod
    @abstractmethod
    def lines(cls, agency_id: str) -> Dict[str, str]:
        """Return a list of transit line IDs -> names for the given agency."""
        pass

    # Properties
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def stations(self) -> Dict[str, str]:
        """Return a dictionary mapping station IDs to station names."""
        pass

    @property
    @abstractmethod
    def agency(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def BASE_URL(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def API_KEY(cls) -> str:
        pass

    @classmethod
    def _send_api_request_json(cls, request_url: str, params: dict) -> dict:
        """Helper method to send API requests and parse JSON responses."""
        response = cls._send_api_request(request_url, params)
        return json.loads(response.content.decode('utf-8-sig'))

    @classmethod
    def _send_api_request(cls, request_url: str, params: dict) -> requests.Response:
        try:
            response = requests.get(request_url, params=params, timeout=5)
            response.raise_for_status()      # Raise error for 4xx / 5xx
            return response
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)
        except ValueError:
            print("Response was not valid JSON")

    def _update_realtime_feed(self):
        """Fetch GTFS-realtime data from API. For now only get from tripupdates endpoint."""
        res = self._send_api_request(
            request_url=f"{self.BASE_URL()}tripupdates",
            params={"api_key": self.API_KEY(), "agency": self.agency}
        )

        # Parse GTFS-realtime feed
        try:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(res.content)
        except Exception as e:
            print("Failed to fetch GTFS-realtime feed:", e)
            return

        # Process feed entities as needed (should all be TripUpdates)
        if self.agency_metadata is None:
            print("Agency metadata not loaded; cannot process real-time feed timestamps correctly.")
            raise ValueError("Agency metadata not loaded")

        tz = ZoneInfo(self.agency_metadata.timezone)
        self.HACK_j_stops: List[StopTime] = []
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip_update = entity.trip_update
                # Prototype: Print the stop_time_updates only for the J line. Times are in the timezone specified by agency.txt
                route_id = None
                if trip_update.trip.route_id in self.routes:
                    route_id = self.routes[trip_update.trip.route_id].name
                if route_id == "J":
                    #print(f"Trip ID: {trip_update.trip.trip_id}, Route ID: {route_id}")
                    for stu in trip_update.stop_time_update:
                        arrival = stu.arrival.time
                        departure = stu.departure.time
                        stop_id = stu.stop_id

                        arrival_str = (
                            datetime.fromtimestamp(arrival, tz).strftime("%H:%M:%S")
                            if arrival else "N/A"
                        )

                        departure_str = (
                            datetime.fromtimestamp(departure, tz).strftime("%H:%M:%S")
                            if departure else "N/A"
                        )
                        #print(f"  Stop ID: {stop_id}, Arrival: {arrival_str}, Departure: {departure_str}")
                        # If the J stop is within 30 seconds of now and is stop ID 16217, save to HACK_j_stops as a StopTime object
                        if stop_id == "16217":
                            now_ts = int(datetime.now(tz).timestamp())
                            if arrival and abs(arrival - now_ts) <= 900:
                                stop_time = StopTime(
                                    trip_id=trip_update.trip.trip_id,
                                    arrival_time=arrival_str,
                                    departure_time=departure_str,
                                    stop_id=stop_id,
                                    stop_sequence=stu.stop_sequence if stu.HasField('stop_sequence') else -1  # Unknown
                                )
                                self.HACK_j_stops.append(stop_time)
                                print("Found one close to Right Of Way/21st St!")
                                print(f"  Trip ID: {trip_update.trip.trip_id} Stop ID: {stop_id}, Arrival: {arrival_str}, Departure: {departure_str}")
            else:
                # Handle other entity types if necessary
                print("Unexpected entity type in GTFS-realtime feed")

    def _read_datafeed(self):
        """Read static GTFS data from downloaded files into memory structures."""
        # For now, just print the available files in the datafeed directory
        datafeed_path = f"datafeeds/{self.agency}/"
        if not os.path.exists(datafeed_path):
            print(f"No datafeed found for agency {self.agency}. Please run update_datafeed() first.")
            return

        # Make sure the needed files exist: agency.txt, routes.txt, stops.txt, trips.txt, stop_times.txt, calendar.txt, calendar_dates.txt
        required_files = [
            "feed_info.txt",
            "agency.txt",
            "routes.txt",
            "stops.txt",
            "trips.txt",
            "stop_times.txt",
            "calendar.txt",
            "calendar_dates.txt"
        ]

        for filename in required_files:
            filepath = os.path.join(datafeed_path, filename)
            if not os.path.isfile(filepath):
                print(f"Required file {filename} not found in datafeed for agency {self.agency}.")
        
        print(f"All required files found for agency {self.agency}.")

        # ---------- Parse feed_info.txt ----------
        with open(os.path.join(datafeed_path, "feed_info.txt"), "r") as f:
            next(f)  # Skip header
            line = f.readline().strip().split(',')
            self.feed_metadata = FeedMetadata(
                feed_publisher_name=line[0],
                feed_publisher_url=line[1],
                feed_lang=line[2],
                feed_start_date=line[3],
                feed_end_date=line[4],
                feed_version=line[5]
            )
            # Print feed metadata for verification
            print(f"Loaded feed metadata: {self.feed_metadata}")

        # ---------- Parse agency.txt ----------
        with open(os.path.join(datafeed_path, "agency.txt"), "r") as f:
            next(f)  # Skip header
            line = f.readline().strip().split(',')
            self.agency_metadata = AgencyMetadata(
                agency_id=line[0],
                name=line[1],
                timezone=line[3]
            )
            # Print agency metadata for verification
            print(f"Loaded agency metadata: {self.agency_metadata}")

        # ---------- Parse stops.txt ----------
        with open(os.path.join(datafeed_path, "stops.txt"), "r") as f:
            next(f)  # Skip header
            for line in f:
                fields = line.strip().split(',')
                stop = Stop(
                    stop_id=fields[0],
                    stop_code=fields[1],
                    name=fields[2],
                    latitude=float(fields[3]),
                    longitude=float(fields[4])
                )
                self.stops[stop.stop_id] = stop
            print(f"Loaded {len(self.stops)} stops.")

        # ---------- Parse routes.txt ----------
        with open(os.path.join(datafeed_path, "routes.txt"), "r") as f:
            next(f)  # Skip header
            for line in f:
                fields = line.strip().split(',')
                route = Route(
                    route_id=fields[0],
                    agency_id=fields[1],
                    name=fields[2]
                )
                self.routes[route.route_id] = route
            print(f"Loaded {len(self.routes)} routes.")

        # ---------- Parse trips.txt ----------
        with open(os.path.join(datafeed_path, "trips.txt"), "r") as f:
            next(f)  # Skip header
            for line in f:
                fields = line.strip().split(',')
                trip = Trip(
                    trip_id=fields[2],
                    block_id=fields[1],
                    route_id=fields[0],
                    service_id=fields[5],
                    direction_id=int(fields[4]),
                    stops={}
                )
                self.trips[trip.trip_id] = trip
            print(f"Loaded {len(self.trips)} trips.")
        # ---------- Parse stop_times.txt ----------
        with open(os.path.join(datafeed_path, "stop_times.txt"), "r") as f:
            next(f)  # Skip header
            for line in f:
                fields = line.strip().split(',')
                stop_time = StopTime(
                    trip_id=fields[0],
                    arrival_time=fields[1],
                    departure_time=fields[2],
                    stop_id=fields[3],
                    stop_sequence=int(fields[4])
                )
                if stop_time.trip_id in self.trips:
                    self.trips[stop_time.trip_id].stops[stop_time.stop_sequence] = stop_time
                else:
                    # TODO: Log warning about stop_time for unknown trip_id
                    pass

            print(f"Loaded stop times for trips.")

        # Print a summary of trips (+ route name) with their # of stop times
        cnt = 0
        for trip_id, trip in self.trips.items():
            route_name = self.routes[trip.route_id].name if trip.route_id in self.routes else "Unknown Route"
            if route_name == "J":
                cnt += 1
                # print(f"Trip ID: {trip_id}, Route Name: {route_name}, Number of Stop Times: {len(trip.stops)}")

        print(f"Total trips on route 'J': {cnt}")