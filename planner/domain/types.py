from dataclasses import dataclass


@dataclass(frozen=True)
class StationCandidate:
    station_id: int
    opis_truckstop_id: str
    name: str
    address: str
    city: str
    state: str
    price_per_gallon: float
    latitude: float
    longitude: float
    along_distance_miles: float
    distance_to_route_miles: float


@dataclass(frozen=True)
class FuelNode:
    key: str
    distance_miles: float
    price_per_gallon: float | None
    purchasable: bool
    station: StationCandidate | None


@dataclass(frozen=True)
class StopAction:
    node: FuelNode
    gallons_purchased: float
    purchase_cost: float
