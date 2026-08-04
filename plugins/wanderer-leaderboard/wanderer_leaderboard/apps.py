"""App Configuration"""

# Django
from django.apps import AppConfig

# Wanderer Leaderboard
from wanderer_leaderboard import __version__


class WandererLeaderboardConfig(AppConfig):
    """App Config"""

    name = "wanderer_leaderboard"
    label = "wanderer_leaderboard"
    verbose_name = f"Wanderer Leaderboard v{__version__}"
    default_auto_field = "django.db.models.AutoField"
