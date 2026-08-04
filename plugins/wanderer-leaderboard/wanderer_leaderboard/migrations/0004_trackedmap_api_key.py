# Django
from django.db import migrations, models


class Migration(migrations.Migration):
    """Put the API fields back to work. The leaderboard now reads Wanderer's
    audit API with a per-map key instead of its Postgres event log, so base_url
    and api_token stop being leftovers and become the whole data path.

    Also picks up help_text edits on map_id/is_active that were never migrated.
    All of this is state only: no column changes reach the database."""

    dependencies = [
        ("wanderer_leaderboard", "0003_switch_to_event_log"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trackedmap",
            name="base_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Wanderer base URL for this map, e.g. "
                    "https://wanderer.example.com. Leave blank to use "
                    "WANDERER_LEADERBOARD_BASE_URL."
                ),
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="trackedmap",
            name="api_token",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Map API key from Wanderer (map settings). Sent as a bearer "
                    "token; without it this map contributes nothing to the "
                    "leaderboard."
                ),
                max_length=255,
                verbose_name="API key",
            ),
        ),
        migrations.AlterField(
            model_name="trackedmap",
            name="map_id",
            field=models.CharField(
                blank=True,
                help_text="Map UUID; optional if slug is set.",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="trackedmap",
            name="is_active",
            field=models.BooleanField(
                default=True, help_text="Include this map in the leaderboard."
            ),
        ),
    ]
