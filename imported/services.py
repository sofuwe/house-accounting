from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import logging
import random
import re
from typing import TYPE_CHECKING, Optional

import pypdfium2 as pdfium

from .interfaces import TransactionInstitutionSource
from .models import Transaction

if TYPE_CHECKING:  # pragma: no cover
    from .interfaces import ITransactionImporter

logger = logging.getLogger(__name__)


class Importer:
    def from_args(source: str, institution: "TransactionInstitutionSource") -> "ITransactionImporter":
        if institution == TransactionInstitutionSource.td_canada.value:
            return TransactionImporterTDCanada(source=source, institution=institution)
        raise Exception(
            f"source:institution combination {source}:{institution.value} not supported."
        )


class TransactionImporterTDCanada(Importer):

    source: str
    institution: "TransactionInstitutionSource"

    transactions_counter = Counter()

    class TransactionRowParser:
        pattern = r"^.*\s[,0-9]+\.[0-9]{2}\s[A-Z]{3}[0-9]{2}(\r|\s[,0-9]+\.[0-9]{2}\r)$"
        line_raw: str

        @classmethod
        def from_line_raw(cls, line_raw: str) -> "TransactionImporterTDCanada.TransactionRowParser":
            assert cls.is_match(line_raw=line_raw)
            instance = cls()
            instance.line_raw = line_raw
            return instance

        def parse(self, year: int) -> tuple[date, str, str, Decimal]:
            pattern_with_balance = r".*\w[,0-9]+\.[0-9]{2}\r"
            if re.match(pattern_with_balance, self.line_raw):
                # Parse amount
                amount_str: str = self.line_raw.split(" ")[-3].replace(",", "")
                amount = Decimal(amount_str)
                # Parse date
                month_day: str = self.line_raw.split(" ")[-2]
                date_str: str = f"{year}{month_day}"
                transaction_date: "date" = datetime.strptime(date_str, "%Y%b%d").date()
            else:
                # Parse date
                month_day: str = self.line_raw.split(" ")[-1].rstrip("\r")
                date_str: str = f"{year}{month_day}"
                transaction_date: "date" = datetime.strptime(date_str, "%Y%b%d").date()
                # Parse amount
                amount_str: str = self.line_raw.split(" ")[-2].replace(",", "")
                amount = Decimal(amount_str)
            # Parse ID
            line_part: str = re.split(r"\s[A-Z]{3}[0-9]{2}", self.line_raw)[0]
            transaction_id_raw: str = re.split(r"\s[,0-9]+\.[0-9]{2}", line_part)[0]
            trx_counter = TransactionImporterTDCanada.transactions_counter
            trx_count = trx_counter.get(transaction_id_raw, 0)
            transaction_id: str = f"{transaction_id_raw}:{transaction_date}:{trx_count}"
            trx_counter[transaction_id_raw] += 1
            return transaction_date, transaction_id_raw, transaction_id, amount

        @classmethod
        def is_match(cls, line_raw: str) -> bool:
            return re.match(cls.pattern, line_raw) is not None

    class DocumentDateRowParser:
        pattern = r"^[A-Z]{3}\s[0-9]{2}\/[0-9]{2}\s-\s[A-Z]{3}\s[0-9]{2}\/[0-9]{2}\r$"
        line_raw: str

        @classmethod
        def from_line_raw(cls, line_raw: str) -> "TransactionImporterTDCanada.DocumentDateRowParser":
            assert cls.is_match(line_raw=line_raw)
            instance = cls()
            instance.line_raw = line_raw
            return instance

        def parse(self) -> tuple[date]:
            pattern_year = r"[0-9]{2}\r$"
            match = re.search(pattern_year, self.line_raw).span()
            year_part = self.line_raw[slice(*re.search(pattern_year, self.line_raw).span())]
            year_str: str = f"20{year_part}".rstrip("\r")
            doc_date = int(year_str)
            return (doc_date,)

        @classmethod
        def is_match(cls, line_raw: str) -> bool:
            return re.match(cls.pattern, line_raw) is not None

    def __init__(self, source: str, institution: "TransactionInstitutionSource") -> None:
        self.source = source
        self.institution = institution

    def process(self) -> None:
        transactions: list["Transaction"] = []

        pdf = pdfium.PdfDocument(self.source)

        texts: list[str] = []
        field_values: dict = {}
        for page in pdf:
            lines: list[str] = page.get_textpage().get_text_range().split("\n")
            year: Optional[int] = None
            for line in lines:
                if self.TransactionRowParser.is_match(line_raw=line):
                    trx_parser = self.TransactionRowParser.from_line_raw(line_raw=line)
                    trx_date, transaction_id_raw, transaction_id, amount = trx_parser.parse(year=year)
                    field_values = dict(
                        date=trx_date,
                        transaction_id_raw=transaction_id_raw,
                        transaction_id=transaction_id,
                        amount=amount,
                    )
                    trx = Transaction(**field_values)
                    transactions.append(trx)
                elif self.DocumentDateRowParser.is_match(line_raw=line):
                    year_parser = self.DocumentDateRowParser.from_line_raw(line_raw=line)
                    year = year_parser.parse()[0]
                texts.append(line)

        # Determine transactions to add vs to update
        existing_transaction_map = dict(
            Transaction.objects
            .filter(transaction_id__in=[t.transaction_id for t in transactions])
            .values_list("transaction_id", "id")
        )
        transaction_ids_existing = set(existing_transaction_map.keys())
        transactions_new = []
        transactions_to_update = []
        for transaction in transactions:
            if transaction.transaction_id not in transaction_ids_existing:
                transactions_new.append(transaction)
            else:
                trx_pkey: int = existing_transaction_map[transaction.transaction_id]
                transaction.pk = trx_pkey
                transactions_to_update.append(transaction)

        # Add new transactions and update existing transactions
        Transaction.objects.bulk_create(transactions_new)
        Transaction.objects.bulk_update(transactions_to_update, fields=tuple(field_values.keys()))
        logger.info("Bulk-created %s new transactions", len(transactions_new))
        logger.info("Bulk-updated %s existing transactions", len(transactions_to_update))
