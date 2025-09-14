from django.db import models


class Transaction(models.Model):
    transaction_id_raw = models.CharField(blank=False, max_length=32)
    transaction_id = models.CharField(blank=False, max_length=32, unique=True)
    account = models.ForeignKey(
        "householdentities.Account",
        on_delete=models.CASCADE,
        related_name="transactions",
        null=False,
        blank=False,
    )
    amount = models.DecimalField(
        null=False,
        decimal_places=4,
        max_digits=12,
    )
    date = models.DateField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.__class__.__name__} ({self.transaction_id}: {self.amount})"
