# Django
from django.db import migrations


class Migration(migrations.Migration):
    """Drop the API-era snapshot tables. The plugin now reads Wanderer's
    user_activity_v1 event log live via unmanaged, read-only models (no tables
    of its own for activity)."""

    dependencies = [
        (
            "wanderer_leaderboard",
            "0002_trackedmap_charactercumulative_dailycontribution",
        ),
    ]

    operations = [
        migrations.DeleteModel(name="DailyContribution"),
        migrations.DeleteModel(name="CharacterCumulative"),
    ]
