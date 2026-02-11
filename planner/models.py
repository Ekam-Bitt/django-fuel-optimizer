from django.db import models


class CityCoordinate(models.Model):
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=8)
    latitude = models.FloatField()
    longitude = models.FloatField()
    source = models.CharField(max_length=32, default="pgeocode")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["city", "state"],
                name="unique_city_state_coordinate",
            ),
        ]
        indexes = [
            models.Index(fields=["state", "city"]),
        ]

    def __str__(self):
        return f"{self.city}, {self.state}"


class FuelStation(models.Model):
    opis_truckstop_id = models.CharField(max_length=64)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=8)
    rack_id = models.CharField(max_length=64)
    retail_price = models.DecimalField(max_digits=8, decimal_places=6)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["retail_price"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return f"{self.truckstop_name} ({self.city}, {self.state})"
