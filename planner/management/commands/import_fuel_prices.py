import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from planner.models import CityCoordinate, FuelStation
from planner.services.city_locator import CityLocator


class Command(BaseCommand):
    help = "Import fuel station prices from CSV into FuelStation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default=str(settings.FUEL_DATA_CSV_PATH),
            help="Path to fuel price CSV file",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing FuelStation rows before import",
        )
        parser.add_argument(
            "--clear-city-cache",
            action="store_true",
            help="Delete CityCoordinate rows before import",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional row cap for local testing",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        rows, unique_cities = self._load_rows(csv_path=csv_path, limit=options["limit"])
        if not rows:
            raise CommandError("No rows found in CSV")

        self.stdout.write(self.style.NOTICE(f"Loaded {len(rows)} rows from CSV"))
        self.stdout.write(self.style.NOTICE(f"Unique city/state pairs: {len(unique_cities)}"))

        with transaction.atomic():
            if options["clear"]:
                deleted = FuelStation.objects.all().delete()[0]
                self.stdout.write(self.style.WARNING(f"Deleted {deleted} FuelStation rows"))
            elif FuelStation.objects.exists():
                raise CommandError("FuelStation table is not empty. Use --clear to avoid duplicate imports.")

            if options["clear_city_cache"]:
                deleted = CityCoordinate.objects.all().delete()[0]
                self.stdout.write(self.style.WARNING(f"Deleted {deleted} CityCoordinate rows"))

            self._ensure_city_coordinates(unique_cities)
            coordinate_map = {
                (coord.city.lower(), coord.state): coord
                for coord in CityCoordinate.objects.filter(
                    city__in=[city for city, _ in unique_cities],
                    state__in=[state for _, state in unique_cities],
                )
            }

            stations, skipped = self._build_station_rows(rows, coordinate_map)
            FuelStation.objects.bulk_create(stations, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(stations)} fuel stations. Skipped {skipped} rows with invalid data.")
        )

    def _load_rows(
        self,
        csv_path: Path,
        limit: int | None,
    ) -> tuple[list[dict[str, str]], set[tuple[str, str]]]:
        rows: list[dict[str, str]] = []
        unique_cities: set[tuple[str, str]] = set()

        with csv_path.open(encoding="utf-8-sig", newline="") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                rows.append(row)
                city = row["City"].strip()
                state = row["State"].strip().upper()
                unique_cities.add((city, state))
                if limit and len(rows) >= limit:
                    break

        return rows, unique_cities

    def _build_station_rows(
        self,
        rows: list[dict[str, str]],
        coordinate_map: dict[tuple[str, str], CityCoordinate],
    ) -> tuple[list[FuelStation], int]:
        stations: list[FuelStation] = []
        skipped_rows = 0

        for row in rows:
            city = row["City"].strip()
            state = row["State"].strip().upper()

            try:
                retail_price = Decimal(row["Retail Price"].strip())
            except (InvalidOperation, AttributeError):
                skipped_rows += 1
                continue

            coord = coordinate_map.get((city.lower(), state))
            latitude = coord.latitude if coord else None
            longitude = coord.longitude if coord else None

            stations.append(
                FuelStation(
                    opis_truckstop_id=row["OPIS Truckstop ID"].strip(),
                    truckstop_name=row["Truckstop Name"].strip(),
                    address=row["Address"].strip(),
                    city=city,
                    state=state,
                    rack_id=row["Rack ID"].strip(),
                    retail_price=retail_price,
                    latitude=latitude,
                    longitude=longitude,
                )
            )

        return stations, skipped_rows

    def _ensure_city_coordinates(self, unique_cities: set[tuple[str, str]]):
        existing = {
            (row["city"].lower(), row["state"])
            for row in CityCoordinate.objects.filter(
                city__in=[city for city, _ in unique_cities],
                state__in=[state for _, state in unique_cities],
            ).values("city", "state")
        }

        missing = [(city, state) for city, state in unique_cities if (city.lower(), state) not in existing]
        if not missing:
            self.stdout.write(self.style.NOTICE("City coordinate cache already complete."))
            return

        self.stdout.write(self.style.NOTICE(f"Resolving coordinates for {len(missing)} city/state pairs with pgeocode"))

        locator = CityLocator()
        inserts: list[CityCoordinate] = []

        for city, state in missing:
            coord = locator.lookup(city=city, state=state)
            if coord is None:
                continue
            inserts.append(
                CityCoordinate(
                    city=city,
                    state=state,
                    latitude=coord.latitude,
                    longitude=coord.longitude,
                    source="pgeocode",
                )
            )

        CityCoordinate.objects.bulk_create(inserts, ignore_conflicts=True, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"Stored {len(inserts)} city coordinate cache rows"))
