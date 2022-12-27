import datetime
from decimal import Decimal
from unicodedata import decimal
from unittest.util import _MAX_LENGTH

from django.db import models


class Transaction(models.Model):

    transaction_id_raw: str = models.CharField(blank=False, max_length=32)
    transaction_id: str = models.CharField(blank=False, max_length=32, unique=True)
    amount: Decimal = models.DecimalField(
        null=False,
        decimal_places=4,
        max_digits=12,
    )
    date: datetime.date = models.DateField(null=False)
