from django.conf import settings
from rest_framework import serializers

EPSILON = 1e-6


class TripPlanRequestSerializer(serializers.Serializer):
    start_location = serializers.CharField(max_length=255)
    finish_location = serializers.CharField(max_length=255)
    mpg = serializers.FloatField(default=settings.ASSIGNMENT_REQUIRED_MPG, min_value=1)
    max_range_miles = serializers.FloatField(
        default=settings.ASSIGNMENT_REQUIRED_MAX_RANGE_MILES,
        min_value=50,
    )
    route_mode = serializers.ChoiceField(
        choices=["direct", "via_stops"],
        default="direct",
    )
    max_stop_detour_miles = serializers.FloatField(
        default=settings.DEFAULT_MAX_STOP_DETOUR_MILES,
        min_value=0,
        allow_null=True,
        required=False,
    )
    min_stop_gallons = serializers.FloatField(
        default=settings.DEFAULT_MIN_STOP_GALLONS,
        min_value=0,
    )
    stop_penalty_usd = serializers.FloatField(
        default=settings.DEFAULT_STOP_PENALTY_USD,
        min_value=0,
    )

    def validate(self, attrs):
        if not settings.ENFORCE_ASSIGNMENT_CONSTRAINTS:
            return attrs

        required_mpg = float(settings.ASSIGNMENT_REQUIRED_MPG)
        required_range = float(settings.ASSIGNMENT_REQUIRED_MAX_RANGE_MILES)

        errors: dict[str, str] = {}
        if abs(float(attrs["mpg"]) - required_mpg) > EPSILON:
            errors["mpg"] = f"Assignment constraint: mpg must be {required_mpg:g}."
        if abs(float(attrs["max_range_miles"]) - required_range) > EPSILON:
            errors["max_range_miles"] = f"Assignment constraint: max_range_miles must be {required_range:g}."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
