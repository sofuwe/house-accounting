from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    fields = (
        "transaction_id",
        "transaction_id_raw",
        "date",
        "amount",
    )
    list_display = (
        "transaction_id_raw",
        "date",
        "amount",
    )
    ordering = ("-date",)
