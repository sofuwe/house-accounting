from django.db import models
from django.contrib.auth.models import User


class ImportAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    source_dir = models.CharField(max_length=255)


class VendorTransactionIdMap(models.Model):
    """Map from Transaction ID (Raw) to Vendor ID."""

    transaction_id_raw = models.CharField(null=False, blank=False, max_length=100)
    vendor_id = models.CharField(null=False, blank=False, max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("transaction_id_raw", "vendor_id"),
                name="uniq_vendor_trx_id_map",
            ),
        ]

    def __str__(self) -> str:
        return f'{self.__class__.__name__}("{self.transaction_id_raw}" -> "{self.vendor_id}")'
