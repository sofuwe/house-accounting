from typing import TYPE_CHECKING

from django.db import models

from .interfaces import TransactionInstitutionSource

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal


class Account(models.Model):
    name: str = models.CharField(
        verbose_name="Unique name of the account",
        unique=True,
        blank=False,
        max_length=200,
    )
    institution: str = models.CharField(
        choices=TransactionInstitutionSource.choices(),
        max_length=50,
    )
    inception_date: "date" = models.DateField(null=False)
    initial_balance: "Decimal" = models.DecimalField(
        null=False,
        default=0,
        max_digits=15,
        decimal_places=4,
    )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
