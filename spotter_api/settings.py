import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value)


def env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return float(raw_value)


def env_optional_float(name: str, default: float | None = None) -> float | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return float(raw_value)


SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "planner",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "spotter_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "spotter_api.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "spotter-locmem-cache",
        "TIMEOUT": 24 * 60 * 60,
    }
}

REST_FRAMEWORK = {
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Spotter Fuel Route Planner API",
    "DESCRIPTION": "Trip routing and fuel stop optimization API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

FUEL_DATA_CSV_PATH = os.getenv(
    "FUEL_DATA_CSV_PATH",
    str(BASE_DIR / "data" / "fuel-prices-for-be-assessment.csv"),
)
OSRM_API_BASE_URL = os.getenv("OSRM_API_BASE_URL", "https://router.project-osrm.org")
NOMINATIM_API_BASE_URL = os.getenv(
    "NOMINATIM_API_BASE_URL",
    "https://nominatim.openstreetmap.org",
)
EXTERNAL_API_TIMEOUT_SECONDS = env_int("EXTERNAL_API_TIMEOUT_SECONDS", 15)
ROUTE_CORRIDOR_MILES = env_float("ROUTE_CORRIDOR_MILES", 60.0)
DEFAULT_MAX_STOP_DETOUR_MILES = env_optional_float("DEFAULT_MAX_STOP_DETOUR_MILES", 20.0)
DEFAULT_MIN_STOP_GALLONS = env_float("DEFAULT_MIN_STOP_GALLONS", 1.5)
DEFAULT_STOP_PENALTY_USD = env_float("DEFAULT_STOP_PENALTY_USD", 1.5)
ENFORCE_ASSIGNMENT_CONSTRAINTS = env_bool("ENFORCE_ASSIGNMENT_CONSTRAINTS", True)
ASSIGNMENT_REQUIRED_MPG = env_float("ASSIGNMENT_REQUIRED_MPG", 10.0)
ASSIGNMENT_REQUIRED_MAX_RANGE_MILES = env_float("ASSIGNMENT_REQUIRED_MAX_RANGE_MILES", 500.0)
GEOLOOKUP_USER_AGENT = os.getenv(
    "GEOLOOKUP_USER_AGENT",
    "spotter-api/1.0 (assignment)",
)

MAP_PROVIDER = os.getenv("MAP_PROVIDER", "auto").strip().lower()
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "")
MAPBOX_DIRECTIONS_PROFILE = os.getenv("MAPBOX_DIRECTIONS_PROFILE", "driving")
