from django.db import models


class General(models.Model):
    """Meta-model that carries app-wide permissions (no DB table)."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access the Wanderer integration"),
        )
