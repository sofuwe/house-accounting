from django.db import models

# Create your models here.


class Config(models.Model):
    """Define the global configuration settings for the application."""

    date_fr = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
