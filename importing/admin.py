from django.contrib import admin

from admin_export_action.admin import export_selected_objects

from .models import VendorTransactionIdMap


@admin.register(VendorTransactionIdMap)
class VendorTransactionIdMapAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id_raw",
        "vendor_id",
    )
    list_filter = ("vendor_id",)

    actions = [export_selected_objects]
