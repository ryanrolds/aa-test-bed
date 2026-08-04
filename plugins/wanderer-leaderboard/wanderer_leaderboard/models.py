"""App Models"""

# Django
from django.db import models

from .managers import TrackedMapManager


class General(models.Model):
    """Meta model for app permissions"""

    class Meta:
        """Meta definitions"""

        managed = False
        default_permissions = ()
        permissions = (("basic_access", "Can access the Wanderer Leaderboard"),)


class TrackedMap(models.Model):

    objects = TrackedMapManager()

    name = models.CharField(max_length=100, help_text="Display name for this map.")
    slug = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Map slug from Wanderer, e.g. 'my-map'. Set this or map_id, not both."
        ),
    )
    map_id = models.CharField(
        max_length=64,
        blank=True,
        help_text=(
            "Map UUID. Alternative to slug — set one or the other, not both; "
            "map_id wins if both are somehow set."
        ),
    )
    is_active = models.BooleanField(
        default=True, help_text="Include this map in the leaderboard."
    )
    base_url = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Base URL used to fetch this map's audit data from Wanderer's API. "
            "Alliance Auth calls it from the server, not your browser, so it must "
            "be reachable from this server — in the Docker setup that is the "
            "wanderer service name (http://wanderer:8000), not http://localhost:8000, "
            "which is Alliance Auth itself. Leave blank to use "
            "WANDERER_LEADERBOARD_BASE_URL."
        ),
    )
    api_token = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="API key",
        help_text=(
            "Map API key from Wanderer (map settings). Sent as a bearer token; "
            "without it this map contributes nothing to the leaderboard."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def has_api_key(self):
        return bool(self.api_token)
