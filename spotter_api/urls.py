from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def root(_request):
    return JsonResponse(
        {
            "service": "spotter-api",
            "status": "ok",
            "endpoints": {
                "admin": "/admin/",
                "trip_plan": {
                    "method": "POST",
                    "path": "/api/trip-plan/",
                },
                "schema": "/api/schema/",
                "swagger_ui": "/api/docs/swagger/",
                "redoc": "/api/docs/redoc/",
            },
        }
    )


urlpatterns = [
    path("", root),
    path("admin/", admin.site.urls),
    path("api/", include("planner.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs-swagger",
    ),
    path(
        "api/docs/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="api-docs-redoc",
    ),
]
