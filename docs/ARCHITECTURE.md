# Architecture Overview

## Request flow
1. `POST /api/trip-plan/` validates payload in `planner/api/serializers.py`.
2. `TripPlanView` delegates orchestration to `planner/services/trip_planner.py`.
3. Trip planner:
   - geocodes start and end (`services/geocoding.py`)
   - fetches one route (`services/routing.py`)
   - computes candidate stations near route (`services/station_locator.py`)
   - computes optimal purchase plan (`domain/optimizer.py`)
4. View returns normalized JSON for clients.

## Layering
- `planner/api`: HTTP/DRF concerns only.
- `planner/domain`: core business logic and immutable planning types.
- `planner/services`: integrations and orchestration.
- `planner/management`: operational commands (CSV import).

## Performance strategy
- route response caching (per provider+coordinates)
- geocoding result caching
- local city/state geocoding first to avoid remote API calls
- station pre-filtering by route bounding box + corridor
- station candidate pruning by distance buckets

## Reliability strategy
- provider mode `auto` (Mapbox fallback to OSRM)
- deterministic errors for invalid route/fuel scenarios
- import guard prevents duplicate bulk imports unless `--clear` is used
- unit tests for API, optimizer, geocoding behavior, routing behavior
