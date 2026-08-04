# Django
from django.db import models


class TrackedMapManager(models.Manager):

    def active(self):
        return self.filter(is_active=True)
