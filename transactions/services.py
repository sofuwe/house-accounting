import datetime as dt
import decimal
from dataclasses import dataclass
from typing import Iterator, Protocol

from householdentities.services import EntityService
from transactions.models import Transaction
from utils import it


class ITransactionInput(Protocol):
    account_id: str
    transaction_id: str
    amount: decimal.Decimal
    date: dt.date


@dataclass
class TransactionForAccount:
    account_id: int
    transaction_id: str
    amount: decimal.Decimal
    date: dt.date
    vendor_id: int


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
                    transactions_update.append(trx_existing)

                else:
                    # Create new transaction
                    transactions_create.append(
                        Transaction(
                            transaction_id=trx.transaction_id,
                            amount=trx.amount,
                            date=trx.date,
                            account_id=account_id_map[trx.account_id],
                        )
                    )

            n_created += len(Transaction.objects.bulk_create(transactions_create))
            n_updated += Transaction.objects.bulk_update(
                transactions_update, fields=["amount", "date", "account_id"]
            )

        return n_created, n_updated


class TransactionReadService:
    def get_transactions_for_accounts(
            self, 
            accounts: list[int],
            date_fr: dt.date,
            date_to: dt.date,
    ) -> Iterator[TransactionForAccount]:
        trx_qs = (
            Transaction.objects
            .filter(account_id__in=accounts, date__range=(date_fr, date_to))
            .values_list("account_id", "transaction_id", "amount", "date", "vendor_id")
        )
        for account_id, trx_id, trx_amount, trx_date, vendor_id in trx_qs.iterator(1000):
            yield TransactionForAccount(
                account_id=account_id,
                transaction_id=trx_id,
                amount=trx_amount,
                date=trx_date,
                vendor_id=vendor_id,
            )

    def get_transaction_to_vendor_id_map(
            self,
            accounts: list[int],
            date_fr: dt.date,
            date_to: dt.date,
    ) -> dict[int, int]:
        qs = (
            Transaction.objects
            .filter(account_id__in=accounts, date__range=(date_fr, date_to))
            .filter(vendor_id__isnull=False)
            .values_list("transaction_id", "vendor_id")
        )
        return {trx_id: trx_vendor_id for trx_id, trx_vendor_id in qs}

    def get_earliest_latest_date(self) -> tuple[dt.date, dt.date] | tuple[None, None]:
        qs = Transaction.objects.values_list("date", flat=True)
        earliest = qs.order_by("date").first()
        latest = qs.order_by("-date").first()
        return (earliest, latest)
