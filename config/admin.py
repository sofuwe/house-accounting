from django.contrib import admin

from .models import Config


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "date_fr", "date_to", "created_at")
    search_fields = ("date_fr", "date_to")
