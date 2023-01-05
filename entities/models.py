from django.db import models

from .interfaces import TransactionInstitutionSource


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

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
