from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    save_as: bool = True
    list_display = ("name", "institution", "inception_date", "initial_balance")
    list_filter = ("institution",)
    search_fields = ("name", "institution")
