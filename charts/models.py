import enum

from django.db import models


class MetricValueQuerySet(models.QuerySet):
    def for_accounts(self, account_ids: list[int]) -> "MetricValueQuerySet":
        return self.filter(account_id__in=account_ids)

    def for_metrics(self, metrics: list[str]) -> "MetricValueQuerySet":
        return self.filter(metric__in=metrics)


class MetricValue(models.Model):

    class Metric(enum.StrEnum):
        Spending = "Spending"

    date = models.DateField(null=False)
    account = models.ForeignKey(
        "householdentities.Account",
        on_delete=models.CASCADE,
        related_name="metric_values",
        null=False,
        blank=False,
    )
    vendor = models.ForeignKey(
        "market_data.Vendor",
        on_delete=models.CASCADE,
        null=False,
    )
    metric = models.CharField(
        max_length=100,
        null=False,
        choices=[(x.value, x.name) for x in Metric],
    )
    value = models.DecimalField(max_digits=10, decimal_places=6, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "account", "vendor", "metric"],
                name="uniq_metric_val",
            ),
        ]

    objects = MetricValueQuerySet.as_manager()
