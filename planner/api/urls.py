from django.urls import path

from planner.api.views import TripPlanView

urlpatterns = [
    path("trip-plan/", TripPlanView.as_view(), name="trip-plan"),
]
