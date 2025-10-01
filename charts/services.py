import datetime as dt
import decimal
import logging
from collections import defaultdict
from typing import Protocol

from pydantic import BaseModel

from charts.models import MetricValue
from market_data.services import MarketDataService
from householdentities.services import EntityService
from transactions.services import TransactionReadService
from utils.dates import get_dates

logger = logging.getLogger(__name__)


class ContributionBDSResult(BaseModel):
    labels: list[str]
    values: list[decimal.Decimal]
    total: decimal.Decimal


class ChartsReadService:
    def __init__(
            self,
            transaction_service: TransactionReadService,
            entity_service: EntityService,
            market_data_service: MarketDataService,
    ):
        self._trx_service = transaction_service
        self._entity_service = entity_service
        self._market_data_service = market_data_service

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
            date_fr=date_fr,
            date_to=date_to,
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

    def get_contribution_bds_as_of(
        self,
        accounts: list[int],
        date_as_of: dt.date,
    ) -> ContributionBDSResult:

        date_fr: dt.date | None = self._entity_service.get_earliest_account_start_date()
        if date_fr is None:
            raise ValueError("No accounts found to determine the earliest start date.")        

        vendor_to_bds_label_map: dict[int, str] = self._market_data_service.get_vendor_to_bds_label_map()

        value_by_bds: dict[str, decimal.Decimal] = defaultdict(decimal.Decimal)
        metric_values = (
            MetricValue.objects
            .for_accounts(accounts)
            .for_metrics([MetricValue.Metric.Spending.value])
            .filter(date=date_as_of)
            .values_list("vendor_id", "value")
        )
        bds_label_default = self._market_data_service.get_campaign_bds_israel_label_default()

        for vendor_id, value in metric_values:
            bds_label = vendor_to_bds_label_map.get(vendor_id, bds_label_default)
            value_by_bds[bds_label] += value

        return ContributionBDSResult(
            labels=list(value_by_bds.keys()),
            values=list(value_by_bds.values()),
            total=sum(value_by_bds.values())
        )


class ITransactionInput(Protocol):
    account_id: int
    transaction_id: str
    amount: decimal.Decimal
    date: dt.date
    vendor_id: int


class ChartsWriteService:
    METRICS: list[MetricValue.Metric] = [
        MetricValue.Metric.Spending,
    ]

    def __init__(
            self,
            entity_service: EntityService,
            txn_rd_service: TransactionReadService,
            charts_rd_service: ChartsReadService,
    ) -> None:
        self._entity_service = entity_service
        self._txn_rd_service = txn_rd_service
        self._charts_rd_service = charts_rd_service

    def track_accounts(
            self,
            accounts: list[int],
            date_fr: dt.date,
            date_to: dt.date,
    ) -> None:
        transactions = self._txn_rd_service.get_transactions_for_accounts(
            accounts=accounts,
            date_fr=date_fr,
            date_to=date_to,
        )

        txns_by_date: dict[dt.date, dict[int, list[ITransactionInput]]] = {
            date_value: defaultdict(list)
            for date_value in get_dates(date_fr=date_fr, date_to=date_to)
        }

        account_to_transactions_map: dict[int, list[ITransactionInput]] = defaultdict(list)
        for txn in transactions:
            account_to_transactions_map[txn.account_id].append(txn)
            txns_by_date[txn.date][txn.account_id].append(txn)

        for date_value, txns_by_account_id in txns_by_date.items():
            metric_value_by_vendor: dict[int, dict[MetricValue.Metric, decimal.Decimal]] = {}
            for account_id, txns in txns_by_account_id.items():
                pass

        for account_id, txns in account_to_transactions_map.items():

            for txn in txns:

                if txn.vendor_id in metric_value_by_vendor:
                    metric_values = metric_value_by_vendor[txn.vendor_id]
                else:
                    metric_values = {}

                for metric in self.METRICS:
                    metric_values_create: list[MetricValue] = []

                    if metric == MetricValue.Metric.Spending:
                        for date, value in self._charts_rd_service.get_value_over_dates(
                            accounts=[account_id],
                            date_fr=date_fr,
                            date_to=date_to,
                        ):
                            metric_values_create.append(
                                MetricValue(
                                    date=date,
                                    account_id=account_id,
                                    metric=MetricValue.Metric.Spending,
                                )
                            )
                    else:
                        raise NotImplementedError

            logger.info(
                "Creating %s metric values [account: %s]",
                len(metric_values_create),
                account_id,
            )
            MetricValue.objects.bulk_create(metric_values_create, ignore_conflicts=True)
