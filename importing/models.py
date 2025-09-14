from django.db import models
from django.contrib.auth.models import User


class ImportAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    source_dir = models.CharField(max_length=255)
