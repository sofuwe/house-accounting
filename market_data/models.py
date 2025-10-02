from django.db import models


class Vendor(models.Model):
    natural_id = models.CharField(unique=True, null=False, blank=False, max_length=100)
    name = models.CharField(max_length=100, null=True, blank=False)

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self.natural_id})"
