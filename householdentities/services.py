import datetime as dt
import decimal
from turtle import update
from typing import Iterable, Iterator, Protocol

from .models import Account, Institution
from utils import it


class IAccountInput(Protocol):
    account_id: str
    name: str
    institution: str
    amount_initial: decimal.Decimal
    date_start: dt.date


class EntityService:
    def get_all_account_ids(self) -> list[int]:
        return list(Account.objects.values_list("id", flat=True))

    def get_account_id_map(self, account_ids: Iterable[str]) -> dict[str, int]:
        qs = Account.objects.filter(natural_id__in=account_ids).values_list("natural_id", "id")
        return {natural_id: account_id for natural_id, account_id in qs}

    def get_amount_initial_map(self, account_ids: list[int]) -> dict[int, tuple[dt.date, decimal.Decimal]]:
        qs = Account.objects.filter(id__in=account_ids).values_list("id", "date_start", "balance_initial")
        return {account_id: (date_start, amount_initial) for account_id, date_start, amount_initial in qs}

    def get_earliest_account_start_date(self) -> dt.date | None:
        return Account.objects.order_by("date_start").values_list("date_start", flat=True).first()

    def bulk_create_or_update_accounts(self, account_ids: Iterator[IAccountInput]) -> tuple[int, int]:
        n_created = 0
        n_updated = 0

        for accounts_chunked in it.iter_chunked(account_ids, size=100):
            natural_ids = {account_in.account_id for account_in in accounts_chunked}
            accounts_existing = {
                account.natural_id: account for account in Account.objects.filter(natural_id__in=natural_ids)
            }

            accounts_update: list[Account] = []
            accounts_create: list[Account] = []

            for account_in in accounts_chunked:
                if account_in.account_id in accounts_existing:
                    account_existing = accounts_existing[account_in.account_id]
                    account_existing.name = account_in.name
                    account_existing.institution = Institution[account_in.institution]
                    account_existing.balance_initial = account_in.amount_initial
                    account_existing.date_start = account_in.date_start
                    accounts_update.append(account_existing)
                else:
                    accounts_create.append(
                        Account(
                            natural_id=account_in.account_id,
                            name=account_in.name,
                            institution=account_in.institution,
                            balance_initial=account_in.amount_initial,
                            date_start=account_in.date_start,
                        ),
                    )

            n_created += len(Account.objects.bulk_create(accounts_create))
            n_updated += Account.objects.bulk_update(
                accounts_update,
                fields=["name", "institution", "balance_initial", "date_start"],
            )

        return n_created, n_updated
