import enum

from django.db import models


class Institution(enum.StrEnum):
    TDCanada = "td_canada"
    KOHO = "koho"


class Account(models.Model):
    natural_id = models.CharField(max_length=100, unique=True, null=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    institution = models.CharField(
        max_length=16,
        choices=[(x.value, x.name) for x in Institution],
        null=False,
    )
    balance_initial = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False)
    date_start = models.DateField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.__class__.__name__} ({self.natural_id}: {self.name})"
