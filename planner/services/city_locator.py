import re
from dataclasses import dataclass

import pgeocode

CITY_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]+")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Coordinate:
    latitude: float
    longitude: float


class CityLocator:
    def __init__(self):
        nominatim = pgeocode.Nominatim("us")
        raw = nominatim._data[["place_name", "state_code", "latitude", "longitude"]].dropna()

        self._city_index: dict[tuple[str, str], list[Coordinate]] = {}
        self._state_fallback: dict[str, Coordinate] = {}
        state_accumulator: dict[str, list[Coordinate]] = {}

        for row in raw.itertuples(index=False):
            state = str(row.state_code).upper().strip()
            city = self._normalize_city(str(row.place_name))
            if not state or not city:
                continue

            coord = Coordinate(latitude=float(row.latitude), longitude=float(row.longitude))
            self._city_index.setdefault((state, city), []).append(coord)
            state_accumulator.setdefault(state, []).append(coord)

        for state, coords in state_accumulator.items():
            mean_lat = sum(coord.latitude for coord in coords) / len(coords)
            mean_lon = sum(coord.longitude for coord in coords) / len(coords)
            self._state_fallback[state] = Coordinate(latitude=mean_lat, longitude=mean_lon)

    @staticmethod
    def _normalize_city(value: str) -> str:
        cleaned = CITY_NORMALIZE_RE.sub(" ", value.lower())
        cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
        return cleaned

    @staticmethod
    def _city_variants(normalized_city: str) -> list[str]:
        variants = [normalized_city]
        if normalized_city.startswith("st "):
            variants.append("saint " + normalized_city[3:])
        if normalized_city.startswith("saint "):
            variants.append("st " + normalized_city[6:])
        if normalized_city.endswith(" city"):
            variants.append(normalized_city.removesuffix(" city"))
        # Keep order deterministic while deduplicating.
        return list(dict.fromkeys(variant for variant in variants if variant))

    def lookup(self, city: str, state: str) -> Coordinate | None:
        normalized_state = state.strip().upper()
        normalized_city = self._normalize_city(city)

        for variant in self._city_variants(normalized_city):
            values = self._city_index.get((normalized_state, variant))
            if values:
                mean_lat = sum(coord.latitude for coord in values) / len(values)
                mean_lon = sum(coord.longitude for coord in values) / len(values)
                return Coordinate(latitude=mean_lat, longitude=mean_lon)

        return self._state_fallback.get(normalized_state)
