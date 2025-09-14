from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("natural_id", "name", "institution", "balance_initial", "date_start", "created_at")
    list_display_links = ("natural_id", "name")
    search_fields = ("natural_id", "name")
    list_filter = ("institution",)
