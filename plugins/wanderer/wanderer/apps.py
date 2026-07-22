from django.apps import AppConfig

from . import __version__


class WandererConfig(AppConfig):
    name = "wanderer"
    label = "wanderer"
    verbose_name = f"Wanderer Integration v{__version__}"
    default_auto_field = "django.db.models.AutoField"
