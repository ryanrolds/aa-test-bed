# Alliance Auth settings override for this test bed.
# Every setting in base.py can be overloaded by redefining it here.
from .base import *  # noqa: F401,F403

SECRET_KEY = os.environ.get("AA_SECRET_KEY")
SITE_NAME = os.environ.get("AA_SITENAME", "Alliance Auth")

# Single, explicit base URL for local dev (upstream builds this from
# PROTOCOL/subdomain/domain; a flat var is simpler for localhost).
SITE_URL = os.environ.get("AA_SITE_URL", "http://localhost:8001")
CSRF_TRUSTED_ORIGINS = [SITE_URL]

DEBUG = os.environ.get("AA_DEBUG", "False") == "True"

DATABASES["default"] = {  # noqa: F405
    "ENGINE": "django.db.backends.mysql",
    "NAME": os.environ.get("AA_DB_NAME"),
    "USER": os.environ.get("AA_DB_USER"),
    "PASSWORD": os.environ.get("AA_DB_PASSWORD"),
    "HOST": os.environ.get("AA_DB_HOST"),
    "PORT": os.environ.get("AA_DB_PORT", "3306"),
    "OPTIONS": {"charset": os.environ.get("AA_DB_CHARSET", "utf8mb4")},
}

# EVE SSO / ESI
ESI_SSO_CALLBACK_URL = f"{SITE_URL}/sso/callback"
ESI_SSO_CLIENT_ID = os.environ.get("ESI_SSO_CLIENT_ID")
ESI_SSO_CLIENT_SECRET = os.environ.get("ESI_SSO_CLIENT_SECRET")
ESI_USER_CONTACT_EMAIL = os.environ.get("ESI_USER_CONTACT_EMAIL")

# Email (disabled verification for local dev)
REGISTRATION_VERIFY_EMAIL = False
EMAIL_HOST = os.environ.get("AA_EMAIL_HOST", "")
EMAIL_PORT = os.environ.get("AA_EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("AA_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("AA_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("AA_EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("AA_DEFAULT_FROM_EMAIL", "")

ROOT_URLCONF = "myauth.urls"
WSGI_APPLICATION = "myauth.wsgi.application"
STATIC_ROOT = "/var/www/myauth/static/"

# Redis broker + cache
BROKER_URL = f"redis://{os.environ.get('AA_REDIS', 'aa_redis:6379')}/0"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.environ.get('AA_REDIS', 'aa_redis:6379')}/1",
    }
}

# Test-bed plugins developed in this repo (installed editable in the image).
INSTALLED_APPS += [  # noqa: F405
    "wanderer_leaderboard",
]

# The leaderboard reads Wanderer's audit API over HTTP, authenticated per map
# with an API key stored on the TrackedMap record (AA admin). This is only the
# fallback base URL for maps that don't set their own; inside compose the
# Wanderer service is reachable by name over the shared wanderer-egress bridge.
WANDERER_LEADERBOARD_BASE_URL = os.environ.get(
    "WANDERER_BASE_URL", "http://wanderer:8000"
)
