"""
Test settings
"""

# flake8: noqa

########################################################
# local.py settings
# Every setting in base.py can be overloaded by redefining it here.

from .base import *

PACKAGE = "wanderer_leaderboard"

SITE_URL = "https://example.com"
CSRF_TRUSTED_ORIGINS = [SITE_URL]

# These are required for Django to function properly. Don't touch.
ROOT_URLCONF = "testauth.urls"
SECRET_KEY = "t$@h+j#yqhmuy$x7$fkhytd&drajgfsb-6+j9pqn*vj0)gq&-2"

# This is where css/images will be placed for your webserver to read
STATIC_ROOT = "/var/www/testauth/static/"

# Change this to change the name of the auth site displayed
# in page titles and the site header.
SITE_NAME = "testauth"

# Change this to enable/disable debug mode, which displays
# useful error messages but can leak sensitive data.
DEBUG = False


LOGGING = False
NOTIFICATIONS_REFRESH_TIME = 30
NOTIFICATIONS_MAX_PER_USER = 50

# Alliance Auth calls django_redis.get_redis_connection("default") during
# app.ready(), so the default cache has to be a real Redis or the test runner
# will not start. Overridable so the suite can run inside the compose stack
# (TESTAUTH_REDIS_URL=redis://aa_redis:6379/15).
#
# Because it is a real, shared Redis, anything that caches must be tested
# behind @override_settings(CACHES=NO_REDIS_CACHE) — otherwise one run serves
# the next run's assertions from the previous run's entries.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("TESTAUTH_REDIS_URL", "redis://127.0.0.1:6379/1"),
    }
}

# Add any additional apps to this list.
INSTALLED_APPS += [
    PACKAGE,
]

# By default, apps are prevented from having public views for security reasons.
# If you want to allow specific apps to have public views,
# you can put their names here (same name as in INSTALLED_APPS).
APPS_WITH_PUBLIC_VIEWS = []

# ------------------------------------------------------------------------------------ #
#
#                                  ESI Settings
#
# ------------------------------------------------------------------------------------ #
ESI_SSO_CLIENT_ID = "dummy"
ESI_SSO_CLIENT_SECRET = "dummy"
ESI_SSO_CALLBACK_URL = "http://localhost:8000"
ESI_USER_CONTACT_EMAIL = "dummy@example.net"


# ------------------------------------------------------------------------------------ #
#
#                                E-Mail Settings
#
# ------------------------------------------------------------------------------------ #
REGISTRATION_VERIFY_EMAIL = False
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = ""

#######################################
# Add any custom settings below here. #
#######################################
