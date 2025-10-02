import datetime as dt
import decimal
import logging
from dataclasses import dataclass
from typing import Iterator, Protocol

from householdentities.services import EntityService
from importing.services import MappingReadService
from market_data.services import MarketDataReadService, MarketDataWriteService
from transactions.models import Transaction
from utils import it

logger = logging.getLogger(__name__)


class ITransactionInput(Protocol):
    account_id: str
    transaction_id: str
    transaction_id_raw: str
    amount: decimal.Decimal
    date: dt.date


@dataclass
class TransactionForAccount:
    transaction_id: str
    amount: decimal.Decimal
    date: dt.date


class TransactionWriteService:
    _entity_service: EntityService

    def __init__(self, entity_service: EntityService) -> None:
        self._entity_service = entity_service

    def bulk_create_or_update_transactions(
        self, transactions: Iterator[ITransactionInput]
    ) -> tuple[int, int]:
        n_created = 0
        n_updated = 0

        for transactions_chunked in it.iter_chunked(transactions, size=100):
            transaction_ids: set[str] = {trx.transaction_id for trx in transactions_chunked}
            transactions_existing: dict[str, Transaction] = {
                trx.transaction_id: trx
                for trx in Transaction.objects.filter(transaction_id__in=transaction_ids)
            }
            account_natural_ids: set[str] = {trx.account_id for trx in transactions_chunked}
            account_id_map: dict[str, int] = self._entity_service.get_account_id_map(
                account_ids=account_natural_ids
            )

            transactions_create: list[Transaction] = []
            transactions_update: list[Transaction] = []

            for trx in transactions_chunked:
                if trx.transaction_id in transactions_existing:
                    # Update existing transaction
                    trx_existing = transactions_existing[trx.transaction_id]
                    trx_existing.amount = trx.amount
                    trx_existing.date = trx.date
                    trx_existing.account_id = account_id_map[trx.account_id]
                    trx_existing.transaction_id_raw = trx.transaction_id_raw
                    transactions_update.append(trx_existing)

                else:
                    # Create new transaction
                    transactions_create.append(
                        Transaction(
                            transaction_id=trx.transaction_id,
                            transaction_id_raw=trx.transaction_id_raw,
                            amount=trx.amount,
                            date=trx.date,
                            account_id=account_id_map[trx.account_id],
                        )
                    )

            n_created += len(Transaction.objects.bulk_create(transactions_create))
            n_updated += Transaction.objects.bulk_update(
                transactions_update,
                fields=["amount", "date", "account_id", "transaction_id_raw"],
            )

        return n_created, n_updated

    def map_transactions_to_vendors(
        self,
        trx_to_vendor_map: dict[str, str],
        vendor_id_map: dict[str, int],
    ) -> int:
        trx_to_update: list[Transaction] = []

        for trx in Transaction.objects.all().only("id"):
            trx_id_raw: str = trx.transaction_id_raw

            if trx_id_raw not in trx_to_vendor_map:
                continue

            vendor_id = trx_to_vendor_map[trx_id_raw]
            trx.vendor_id = vendor_id_map[vendor_id]

            trx_to_update.append(trx)

        return Transaction.objects.bulk_update(trx_to_update, fields=["vendor_id"])


class TransactionReadService:
    def get_transactions_for_accounts(self, accounts: list[int]) -> Iterator[TransactionForAccount]:
        for trx in Transaction.objects.filter(account_id__in=accounts):
            yield TransactionForAccount(
                transaction_id=trx.transaction_id,
                amount=trx.amount,
                date=trx.date,
            )

    def get_earliest_latest_date(self) -> tuple[dt.date, dt.date] | tuple[None, None]:
        qs = Transaction.objects.values_list("date", flat=True)
        earliest = qs.order_by("date").first()
        latest = qs.order_by("-date").first()
        return (earliest, latest)


class TransactionMappingService:
    def __init__(
        self,
        mapping_rd_svc: MappingReadService,
        market_data_rd_svc: MarketDataReadService,
        market_data_wr_svc: MarketDataWriteService,
        trx_wr_svc: TransactionWriteService,
    ):
        self._mapping_rd_svc = mapping_rd_svc
        self._market_data_rd_svc = market_data_rd_svc
        self._market_data_wr_svc = market_data_wr_svc
        self._trx_wr_svc = trx_wr_svc

    def map_transactions_to_vendors(self):
        trx_to_vendor_map = self._mapping_rd_svc.get_trx_to_vendor_map()

        vendors_to_create: list[tuple[str, str]] = []
        vendor_id_map = self._market_data_rd_svc.get_vendor_id_map()
        for vendor_id in trx_to_vendor_map.values():
            if vendor_id not in vendor_id_map:
                vendors_to_create.append((vendor_id, vendor_id))

        vendors_created, _ = self._market_data_wr_svc.bulk_create_or_update_vendors(
            vendors_to_create,
        )
        logger.debug("Created %s new vendors", vendors_created)

        count: int = self._trx_wr_svc.map_transactions_to_vendors(
            trx_to_vendor_map=trx_to_vendor_map,
            vendor_id_map=self._market_data_rd_svc.get_vendor_id_map(),
        )
        logger.debug("Mapped %s transactions to vendors", count)
