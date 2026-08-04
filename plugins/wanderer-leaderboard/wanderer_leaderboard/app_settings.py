"""App Settings"""

# Django
from django.conf import settings

# Wanderer base URL used for tracked maps that don't set their own.
WANDERER_BASE_URL = getattr(
    settings, "WANDERER_LEADERBOARD_BASE_URL", "http://wanderer:8000"
)

# Seconds to wait on the map API before giving up.
API_TIMEOUT = getattr(settings, "WANDERER_LEADERBOARD_API_TIMEOUT", 30)

# How long an audit response is cached. One fetch covers three months of events,
# so re-pulling it for every page view (and every month the user pages through)
# is pure waste.
CACHE_TTL = getattr(settings, "WANDERER_LEADERBOARD_CACHE_TTL", 300)
