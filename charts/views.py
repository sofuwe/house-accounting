import calendar
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from django.views.generic import TemplateView

from charts.services import ChartService
from config.services import ConfigReadService
from householdentities.services import EntityService
from transactions.services import TransactionReadService

if TYPE_CHECKING:  # pragma: no cover
    from django.http import HttpRequest, HttpResponse


class CurrentBalancesChartView(TemplateView):
    template_name = "current-balance.html"

    def get(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> "HttpResponse":
        year_month = request.GET.get("year-month")
        kwargs = dict(**kwargs, year_month=year_month)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if kwargs.get("year_month"):
            date_start = datetime.strptime(kwargs["year_month"], "%Y-%m").date()
            _, month_days = calendar.monthrange(date_start.year, date_start.month)
            date_end = date_start + timedelta(days=month_days)
        else:
            entity_service = EntityService()
            config_service = ConfigReadService()
            config_latest = config_service.get_latest_config()
            assert config_latest is not None, "No config found, please create one first."
            date_start = config_latest.date_fr
            date_end = config_latest.date_to
            assert date_start is not None and date_end is not None, "Config dates cannot be None."

        trx_service = TransactionReadService()
        entity_service = EntityService()
        chart_service = ChartService(
            transaction_service=trx_service,
            entity_service=entity_service,
        )
        current_balances = chart_service.get_value_over_dates(
            accounts=entity_service.get_all_account_ids(),
            date_fr=date_start,
            date_to=date_end,
        )

        days_sorted = [date_start + timedelta(days=i) for i in range((date_end - date_start).days + 1)]
        context["current_balances"] = [(str(days_sorted[i]), balance) for i, balance in current_balances]

        return context
