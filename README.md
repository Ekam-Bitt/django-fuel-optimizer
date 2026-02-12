# Spotter Fuel Route Planner API

Production-structured Django backend for trip routing + fuel cost optimization.

For design details, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What it does
- Accepts `start_location` and `finish_location` (US)
- Builds a driving route using a single routing API call
- Finds cost-effective fuel stops along that route (500-mile range default)
- Returns full route geometry and total estimated fuel cost (10 MPG default)

## Tech stack
- Python 3.13+
- Django 6 + Django REST Framework
- drf-spectacular (OpenAPI + Swagger/ReDoc)
- python-dotenv (`.env` auto-loading)
- Mapbox Directions API (primary)
- OSRM (fallback or standalone provider)
- SQLite

## Project structure
```text
spotter/
  planner/
    api/
      serializers.py
      urls.py
      views.py
    domain/
      optimizer.py
      types.py
    management/commands/
      import_fuel_prices.py
    services/
      city_locator.py
      distance.py
      geocoding.py
      routing.py
      station_locator.py
      trip_planner.py
    tests/
      test_api.py
      test_geocoding.py
      test_optimizer.py
      test_routing.py
    admin.py
    models.py
  spotter_api/
    settings.py
    urls.py
  data/
    fuel-prices-for-be-assessment.csv
  docs/
    ARCHITECTURE.md
    Django_Developer_Assignment.txt
  .github/workflows/
    ci.yml
  requirements/
    base.txt
    development.txt
```

## Setup
```bash
cd /Users/ekambitt/Projects/spotter
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements/base.txt
```

or:
```bash
make setup
```

for linting tools:
```bash
pip install -r requirements/development.txt
```

## Configuration
```bash
cp .env.example .env
# fill MAPBOX_ACCESS_TOKEN and adjust values as needed
```

`.env` is loaded automatically by Django settings via `python-dotenv`.

Important environment variables:
- `MAP_PROVIDER=auto` (tries Mapbox then OSRM)
- `MAPBOX_ACCESS_TOKEN=...`
- `ROUTE_CORRIDOR_MILES=60`
- `DEFAULT_MAX_STOP_DETOUR_MILES=20`
- `DEFAULT_MIN_STOP_GALLONS=1.5`
- `DEFAULT_STOP_PENALTY_USD=1.5`
- `ENFORCE_ASSIGNMENT_CONSTRAINTS=true`
- `ASSIGNMENT_REQUIRED_MPG=10`
- `ASSIGNMENT_REQUIRED_MAX_RANGE_MILES=500`
- `EXTERNAL_API_TIMEOUT_SECONDS=15`

## Database + data import
```bash
. .venv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py import_fuel_prices --clear
```

or:
```bash
make migrate
make import
```

Import safety:
- If `FuelStation` already has rows and `--clear` is not passed, import exits to prevent accidental duplicates.

## Run
```bash
. .venv/bin/activate
python manage.py runserver
```

## OpenAPI / Swagger
- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/swagger/`
- ReDoc: `GET /api/docs/redoc/`

## API
### `POST /api/trip-plan/`

Assignment constraints enforced by default:
- `mpg` must be `10`
- `max_range_miles` must be `500`

Request body:
```json
{
  "start_location": "Chicago, IL",
  "finish_location": "Dallas, TX",
  "mpg": 10,
  "max_range_miles": 500,
  "route_mode": "direct",
  "max_stop_detour_miles": 20,
  "min_stop_gallons": 1.5,
  "stop_penalty_usd": 1.5
}
```

`route_mode` options:
- `direct` (default): one route from origin to destination, stops optimized near this route
- `via_stops`: computes an additional waypoint geometry through selected fuel stops for map visualization

Optimization tuning fields:
- `max_stop_detour_miles` (float, nullable): maximum station offset from route used for planning
- `min_stop_gallons` (float): discourages tiny top-up stops when feasible
- `stop_penalty_usd` (float): per-stop virtual penalty to prefer fewer stops when cost difference is small
- Set `min_stop_gallons=0` and `stop_penalty_usd=0` for strict cost-only behavior.
- To allow non-assignment vehicle values, set `ENFORCE_ASSIGNMENT_CONSTRAINTS=false`.

Example:
```bash
curl -X POST http://127.0.0.1:8000/api/trip-plan/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_location": "Chicago, IL",
    "finish_location": "Dallas, TX",
    "mpg": 10,
    "max_range_miles": 500,
    "route_mode": "via_stops",
    "max_stop_detour_miles": 20,
    "min_stop_gallons": 1.5,
    "stop_penalty_usd": 1.5
  }'
```

Response includes:
- resolved origin/destination coordinates
- route distance, duration, and GeoJSON polyline
- optimized fuel stops with purchase gallons and stop-level cost
- total estimated fuel spend
- metadata (`route_api_calls`, provider, station candidate counts)

## Quality checks
```bash
. .venv/bin/activate
python manage.py check
python manage.py test
make lint
```


## CI
- GitHub Actions workflow: `.github/workflows/ci.yml`
- Runs Django checks, migration drift check, lint, and tests on push/PR.

## Assignment notes
- Routing is done once per request and cached.
- Geocoding is optimized to prefer local city/state lookup first, then Nominatim fallback.
- Fuel station coordinates are city/state approximations derived from postal geography.
