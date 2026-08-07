# Django
from django.db import migrations, models


class Migration(migrations.Migration):
    """Require a base URL per map and drop the WANDERER_LEADERBOARD_BASE_URL
    fallback that used to fill it in.

    The setting defaulted to a Docker service name, so a map saved without a URL
    silently pointed at a host that only exists in the author's compose stack.
    A map has to know where its Wanderer lives; that is per map data, not
    instance configuration.

    Form level only — the column is unchanged and existing rows keep whatever
    they hold. A row left empty now raises a clear error instead of fetching
    from nowhere."""

    dependencies = [
        ("wanderer_leaderboard", "0006_alter_trackedmap_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trackedmap",
            name="base_url",
            field=models.CharField(
                help_text=(
                    "Base URL of the Wanderer instance hosting this map, e.g. "
                    "https://wanderer.example.com. Alliance Auth calls it from "
                    "the server, not from your browser, so it has to be "
                    "reachable from this server — behind Docker that is usually "
                    "the Wanderer service name, not the localhost address you "
                    "use in the browser."
                ),
                max_length=255,
            ),
        ),
    ]
