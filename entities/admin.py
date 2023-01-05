from django.contrib import admin

from .models import Account

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "institution")
    list_filter = ("institution",)
    search_fields = ("name", "institution")
