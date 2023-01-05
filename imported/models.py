import datetime
from decimal import Decimal
from unicodedata import decimal
from unittest.util import _MAX_LENGTH

from django.db import models

from entities.models import Account


class Transaction(models.Model):

    account: "Account" = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=False,
    )
    transaction_id_raw: str = models.CharField(blank=False, max_length=32)
    transaction_id: str = models.CharField(blank=False, max_length=32, unique=True)
    amount: Decimal = models.DecimalField(
        null=False,
        decimal_places=4,
        max_digits=12,
    )
    date: datetime.date = models.DateField(null=False)
