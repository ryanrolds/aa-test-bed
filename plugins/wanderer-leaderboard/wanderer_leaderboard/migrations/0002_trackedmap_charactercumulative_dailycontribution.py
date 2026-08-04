# Django
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wanderer_leaderboard", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrackedMap",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Display name for this map.", max_length=100
                    ),
                ),
                (
                    "base_url",
                    models.CharField(
                        default="http://wanderer:8000",
                        help_text="Base URL of the Wanderer instance (no trailing slash).",
                        max_length=255,
                    ),
                ),
                (
                    "slug",
                    models.CharField(
                        blank=True,
                        help_text="Map slug (e.g. 'my-map').",
                        max_length=100,
                    ),
                ),
                (
                    "map_id",
                    models.CharField(
                        blank=True,
                        help_text="Map UUID (alternative to slug).",
                        max_length=64,
                    ),
                ),
                (
                    "api_token",
                    models.CharField(
                        help_text="Wanderer Map API token (Bearer).", max_length=255
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Collect activity for this map."
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="CharacterCumulative",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("eve_character_id", models.CharField(max_length=20)),
                ("character_name", models.CharField(blank=True, max_length=100)),
                ("corporation_ticker", models.CharField(blank=True, max_length=10)),
                ("alliance_ticker", models.CharField(blank=True, max_length=10)),
                ("connections", models.PositiveIntegerField(default=0)),
                ("signatures", models.PositiveIntegerField(default=0)),
                ("passages", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "map",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cumulative",
                        to="wanderer_leaderboard.trackedmap",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DailyContribution",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("eve_character_id", models.CharField(max_length=20)),
                ("date", models.DateField()),
                ("connections", models.PositiveIntegerField(default=0)),
                ("signatures", models.PositiveIntegerField(default=0)),
                ("passages", models.PositiveIntegerField(default=0)),
                (
                    "map",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contributions",
                        to="wanderer_leaderboard.trackedmap",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="charactercumulative",
            constraint=models.UniqueConstraint(
                fields=("map", "eve_character_id"), name="uniq_cumulative_map_character"
            ),
        ),
        migrations.AddIndex(
            model_name="dailycontribution",
            index=models.Index(
                fields=["map", "date"], name="wanderer_le_map_id_c2e9f6_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="dailycontribution",
            constraint=models.UniqueConstraint(
                fields=("map", "eve_character_id", "date"),
                name="uniq_daily_map_character_date",
            ),
        ),
    ]
