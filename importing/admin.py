from django.contrib import admin

from .models import VendorTransactionIdMap


@admin.register(VendorTransactionIdMap)
class VendorTransactionIdMapAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id_raw",
        "vendor_id",
    )
    list_filter = ("vendor_id",)
