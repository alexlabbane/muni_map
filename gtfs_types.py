from dataclasses import dataclass
from typing import Dict, List

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