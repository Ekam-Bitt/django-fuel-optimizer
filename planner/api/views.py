from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from requests import HTTPError, RequestException
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from planner.api.serializers import TripPlanRequestSerializer
from planner.domain.optimizer import FuelPlanningError
from planner.services.geocoding import GeocodingError
from planner.services.routing import RoutingError
from planner.services.trip_planner import build_trip_plan


class TripPlanView(APIView):
    @extend_schema(
        request=TripPlanRequestSerializer,
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Trip plan result."),
            400: OpenApiResponse(description="Validation or planning error."),
            502: OpenApiResponse(description="Upstream API/network error."),
        },
    )
    def post(self, request):
        serializer = TripPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data
        try:
            result = build_trip_plan(
                start_location=payload["start_location"],
                end_location=payload["finish_location"],
                mpg=payload["mpg"],
                max_range_miles=payload["max_range_miles"],
                route_mode=payload["route_mode"],
                max_stop_detour_miles=payload["max_stop_detour_miles"],
                min_stop_gallons=payload["min_stop_gallons"],
                stop_penalty_usd=payload["stop_penalty_usd"],
            )
        except (GeocodingError, RoutingError, FuelPlanningError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except HTTPError as exc:
            return Response(
                {"detail": f"External API error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except RequestException as exc:
            return Response(
                {"detail": f"Network error while calling external service: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result, status=status.HTTP_200_OK)
