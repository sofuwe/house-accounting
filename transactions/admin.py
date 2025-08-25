from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "account__natural_id", "account__name", "amount", "date", "created_at")
    list_display_links = ("transaction_id", "account__natural_id")
    search_fields = ("transaction_id", "date")
    list_filter = ("account__natural_id", "account__name")
