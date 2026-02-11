from rest_framework import serializers


class TripPlanRequestSerializer(serializers.Serializer):
    start_location = serializers.CharField(max_length=255)
    finish_location = serializers.CharField(max_length=255)
    mpg = serializers.FloatField(default=10.0, min_value=1)
    max_range_miles = serializers.FloatField(default=500.0, min_value=50)
