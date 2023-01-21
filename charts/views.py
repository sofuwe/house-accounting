from collections import defaultdict
from calendar import mdays
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db.models import Max, Min, Sum
from django.shortcuts import render
from django.views.generic import TemplateView

from entities.models import Account
from imported.models import Transaction

if TYPE_CHECKING:  # pragma: no cover
    from django.http import HttpRequest, HttpResponse


class CurrentBalancesChartView(TemplateView):
    template_name = 'current-balance.html'

    def get(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> "HttpResponse":
        year_month = request.GET.get("year-month")
        kwargs = dict(**kwargs, year_month=year_month)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if kwargs.get("year_month"):
            date_start = datetime.strptime(kwargs["year_month"], "%Y-%m").date()
            date_end = date_start + timedelta(days=mdays[date_start.month])
        else:
            dates_min_max: dict[str, date] = (
                Transaction.objects.aggregate(Min("date"), Max("date"))
            )
            date_start = dates_min_max["date__min"]
            date_end = dates_min_max["date__max"]

        qs = (
            Transaction.objects
            .filter(date__gte=date_start)
            .filter(date__lt=date_end)
            .values_list("date", "amount")
        )

        # DEBUG START
        tx_by_date = defaultdict(list)
        for cur_date, cur_amount, trx_id_raw in qs.values_list("date", "amount", "transaction_id_raw"):
            tx_by_date[cur_date].append((trx_id_raw, cur_amount))
        # DEBUG END

        # starting_balance_trx: Decimal = (
        #     Transaction.objects
        #     .filter(date__lt=date_start)
        #     .aggregate(Sum("amount"))
        # )["amount__sum"] or Decimal()
        starting_balance_accounts: Decimal = (
            Account.objects.aggregate(Sum("initial_balance"))
        )["initial_balance__sum"] or Decimal()

        current_value_map: dict[date, Decimal] = defaultdict(Decimal)
        for cur_date, cur_amount in qs:
            current_value_map[cur_date] += cur_amount
        
        days_sorted = [
            date_start + timedelta(days=i)
            for i in range((date_end - date_start).days + 1)
        ]

        for i, day in enumerate(days_sorted):
            if i == 0:
                current_value_map[day] += starting_balance_accounts
            else:
                day_before = days_sorted[i - 1]
                current_value_map[day] += current_value_map[day_before]

        current_balances = [
            (i, current_value_map[cur_date]) 
            for i, cur_date in enumerate(days_sorted)
        ]

        context["current_balances"] = current_balances
        return context
