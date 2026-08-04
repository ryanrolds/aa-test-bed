# Django
from django.db import migrations, models


class Migration(migrations.Migration):
    """Help_text wording only, no column changes.

    base_url: the old text read like a display setting, so pasting the browser's
    http://localhost:8000 was the obvious move — and inside the container that
    host is Alliance Auth itself, which answers the audit request with a 404.

    slug/map_id: say plainly that they're alternatives. The admin now picks one
    via a dropdown, but the model is still reachable directly."""

    dependencies = [
        ("wanderer_leaderboard", "0004_trackedmap_api_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trackedmap",
            name="base_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Base URL used to fetch this map's audit data from Wanderer's "
                    "API. Alliance Auth calls it from the server, not your browser, "
                    "so it must be reachable from this server — in the Docker setup "
                    "that is the wanderer service name (http://wanderer:8000), not "
                    "http://localhost:8000, which is Alliance Auth itself. Leave "
                    "blank to use WANDERER_LEADERBOARD_BASE_URL."
                ),
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="trackedmap",
            name="slug",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Map slug from Wanderer, e.g. 'my-map'. Set this or map_id, "
                    "not both."
                ),
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="trackedmap",
            name="map_id",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Map UUID. Alternative to slug — set one or the other, not "
                    "both; map_id wins if both are somehow set."
                ),
                max_length=64,
            ),
        ),
    ]
