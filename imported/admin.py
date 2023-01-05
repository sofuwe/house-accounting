from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    fields = (
        "account",
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
    list_filter = ("date", "account__name")
    search_fields = ("date", "account__name")
    ordering = ("-date",)
