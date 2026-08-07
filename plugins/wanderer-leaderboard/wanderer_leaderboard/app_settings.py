"""App Settings

Read through a module ``__getattr__`` rather than bound at import time, so that
a setting changed after startup — most often by ``override_settings`` in a test
— is actually seen by the code that reads it.
"""

# Django
from django.conf import settings

_DEFAULTS = {
    # Seconds to wait on the map API before giving up.
    "API_TIMEOUT": ("WANDERER_LEADERBOARD_API_TIMEOUT", 30),
    # How long an audit response is cached. One fetch covers three months of
    # events, so re-pulling it for every page view (and every month the user
    # pages through) is pure waste.
    "CACHE_TTL": ("WANDERER_LEADERBOARD_CACHE_TTL", 300),
}


def __getattr__(name):
    try:
        setting_name, default = _DEFAULTS[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None

    return getattr(settings, setting_name, default)


def __dir__():
    return sorted([*globals(), *_DEFAULTS])
