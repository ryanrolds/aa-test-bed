# Django
from django.db import migrations


class Migration(migrations.Migration):
    """Order tracked maps by name.

    Without it the map picker and the fetch order were whatever the database
    returned. Options only: no column changes reach the database."""

    dependencies = [
        ("wanderer_leaderboard", "0005_alter_trackedmap_base_url"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="trackedmap",
            options={
                "ordering": ["name"],
                "verbose_name": "tracked map",
                "verbose_name_plural": "tracked maps",
            },
        ),
    ]
