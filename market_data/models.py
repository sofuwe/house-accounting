import uuid
from django.db import models


class CampaignBDSIsrael(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    natural_id = models.CharField(max_length=100, unique=True, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    is_default = models.BooleanField(default=False)


class Vendor(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    natural_id = models.CharField(max_length=100, unique=True, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)

    #
    # BEGIN MarketData attributes:

    campaign_bds_israel = models.ForeignKey(CampaignBDSIsrael, on_delete=models.CASCADE)

    # END MarketData attributes

    def __str__(self):
        return f"{self.__class__.__name__} ({self.id}: {self.name})"
