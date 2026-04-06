from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

# Static GTFS Data - should be primary keyed by first field
# TODO: Still need to decide the best way to organize the data to make it easy to query/update with real-time feed

# From feed_info.txt
@dataclass
class FeedMetadata:
    feed_publisher_name: str
    feed_publisher_url: str
    feed_lang: str
    feed_start_date: str
    feed_end_date: str
    feed_version: str

# From agency.txt
@dataclass
class AgencyMetadata:
    agency_id: str
    name: str
    timezone: str

    def current_time_in_timezone(self) -> datetime:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(self.timezone))

# From stops.txt
@dataclass
class Stop:
    stop_id: str
    stop_code: str
    name: str
    latitude: float
    longitude: float

# From routes.txt
@dataclass
class Route:
    route_id: str
    agency_id: str
    name: str
    trips: Dict[str, 'Trip']  # Keyed by trip_id

# From trips.txt
@dataclass
class Trip:
    trip_id: str
    block_id: str
    route_id: str
    service_id: str
    direction_id: int
    stops: Dict[int, 'StopTime']  # Keyed by stop_sequence

# From stop_times.txt
@dataclass
class StopTime:
    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int
    arrival_real_time: bool = False  # Indicates if this stop time has been updated with real-time data
    departure_real_time: bool = False  # Indicates if this stop time has been updated with real-time data

    def time_to_departure_seconds(self, current_time) -> int:
        """Calculate time to departure in seconds from current_time (HH:MM:SS or datetime)."""
        if not self.departure_time or self.departure_time.strip() == "":
            return None

        try:
            h1, m1, s1 = map(int, self.departure_time.split(":"))
            dep_seconds = h1 * 3600 + m1 * 60 + s1

            # Handle both datetime objects and strings
            if hasattr(current_time, 'hour'):
                # It's a datetime object
                h2, m2, s2 = current_time.hour, current_time.minute, current_time.second
            else:
                # It's a string
                h2, m2, s2 = map(int, current_time.split(":"))

            curr_seconds = h2 * 3600 + m2 * 60 + s2

            # Edge case: if the current time is just before midnight and departure is just after midnight,
            # departure time should be considered as next day
            if dep_seconds < curr_seconds:
                dep_seconds += 24 * 3600

            return dep_seconds - curr_seconds
        except (ValueError, AttributeError):
            return None

    def time_to_arrival_seconds(self, current_time) -> int:
        """Calculate time to arrival in seconds from current_time (HH:MM:SS or datetime)."""
        if not self.arrival_time or self.arrival_time.strip() == "":
            return None

        try:
            h1, m1, s1 = map(int, self.arrival_time.split(":"))
            arr_seconds = h1 * 3600 + m1 * 60 + s1

            # Handle both datetime objects and strings
            if hasattr(current_time, 'hour'):
                # It's a datetime object
                h2, m2, s2 = current_time.hour, current_time.minute, current_time.second
            else:
                # It's a string
                h2, m2, s2 = map(int, current_time.split(":"))

            curr_seconds = h2 * 3600 + m2 * 60 + s2

            # Edge case: if the current time is just before midnight and arrival is just after midnight,
            # arrival time should be considered as next day
            if arr_seconds < curr_seconds:
                arr_seconds += 24 * 3600

            return arr_seconds - curr_seconds
        except (ValueError, AttributeError):
            return None

# TODO: Figure out exactly how we need to use this one...
# Default is every day of week service if no calendar is listed
# From calendar.txt
@dataclass
class ServiceCalendar:
    service_id: str
    start_date: str
    end_date: str
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    exceptions: List['ServiceException']
    
# From calendar_dates.txt
@dataclass
class ServiceException:
    service_id: str
    date: str
    exception_type: int  # 1 for added service, 2 for removed service