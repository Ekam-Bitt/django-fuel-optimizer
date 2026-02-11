from django.contrib import admin

from planner.models import CityCoordinate, FuelStation


@admin.register(CityCoordinate)
class CityCoordinateAdmin(admin.ModelAdmin):
    list_display = ("city", "state", "latitude", "longitude", "source", "updated_at")
    search_fields = ("city", "state")


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = (
        "truckstop_name",
        "city",
        "state",
        "retail_price",
        "latitude",
        "longitude",
    )
    list_filter = ("state",)
    search_fields = ("truckstop_name", "city", "state", "address")
