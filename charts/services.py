from collections import defaultdict
import datetime as dt
import decimal
from email.policy import default
from typing import Iterator, Protocol

from householdentities.services import EntityService
from transactions.services import TransactionReadService


class ITransactionInput(Protocol):
    transaction_id: str
    amount: decimal.Decimal
    date: dt.date


class ChartService:
    def __init__(self, transaction_service: TransactionReadService, entity_service: EntityService):
        self._trx_service = transaction_service
        self._entity_service = entity_service

    def get_value_over_dates(
        self,
        accounts: list[int],
        date_fr: dt.date,
        date_to: dt.date,
    ) -> list[tuple[int, decimal.Decimal]]:
        mv_init_by_account: dict[int, tuple[dt.date, decimal.Decimal]]
        mv_init_by_account = self._entity_service.get_amount_initial_map(
            accounts,
        )
        mv_init_by_date: dict[dt.date, decimal.Decimal] = defaultdict(decimal.Decimal)
        for date_start, amount_initial in mv_init_by_account.values():
            mv_init_by_date[date_start] += amount_initial

        mv_by_date: dict[dt.date, decimal.Decimal] = defaultdict(decimal.Decimal)
        trx_iter = self._trx_service.get_transactions_for_accounts(
            accounts=accounts,
        )
        for trx in trx_iter:
            mv_by_date[trx.date] += trx.amount

        dates: list[dt.date] = [date_fr + dt.timedelta(days=i) for i in range((date_to - date_fr).days + 1)]

        result = []
        mv: decimal.Decimal = decimal.Decimal()
        for i, date_value in enumerate(dates):
            if date_value in mv_init_by_date:
                mv += mv_init_by_date[date_value]
            if date_value in mv_by_date:
                mv += mv_by_date[date_value]
            result.append((i, mv))

        return result
