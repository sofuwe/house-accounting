from collections import Counter
import csv
from datetime import date, datetime
from decimal import Decimal
import logging
import random
import re
from time import strptime
from typing import TYPE_CHECKING, Iterator, Optional, TypedDict
from django.forms import ValidationError

import pypdfium2 as pdfium

from entities.models import Account
from .interfaces import TransactionInstitutionSource
from .models import Transaction

if TYPE_CHECKING:  # pragma: no cover
    from .interfaces import ITransactionImporter

logger = logging.getLogger(__name__)


class Importer:

    source: str
    institution: "TransactionInstitutionSource"
    account: "Account"
    transactions_counter: "Counter"

    def __init__(
        self,
        source: str,
        institution: "TransactionInstitutionSource",
        account: "Account",
    ) -> None:
        self.source = source
        self.institution = institution
        self.account = account
        self.transactions_counter = Counter()

    @classmethod
    def from_args(
        cls,
        source: str,
        institution: "TransactionInstitutionSource",
        account: "Account",
    ) -> "Importer":
        instance = cls(source=source, institution=institution, account=account)
        return instance

    def process(self) -> None:
        implementor: "ITransactionImporter" = self._get_implentor()
        implementor.process()

    def _get_implentor(self) -> "ITransactionImporter":
        kwargs = dict(
            source=self.source, 
            institution=self.institution,
            account=self.account,
        )
        if self.institution == TransactionInstitutionSource.td_canada.value:
            if self.source.endswith(".pdf"):
                return TransactionImporterTDCanadaPDF(**kwargs)
            elif self.source.endswith(".csv"):
                return TransactionImporterTDCanadaCSV(**kwargs)
        elif self.institution == TransactionInstitutionSource.koho:
            if self.source.endswith(".csv"):
                return TransactionImporterKOHOCSV(**kwargs)
        raise Exception(
            f"'source:institution' combination '{self.source}:{self.institution.value}'"
            " not supported."
        )


class TransactionImporterTDCanadaPDF(Importer):

    class TransactionRowParser:
        pattern = r"^.*\s[,0-9]+\.[0-9]{2}\s[A-Z]{3}[0-9]{2}(\r|\s[,0-9]+\.[0-9]{2}\r)$"
        line_raw: str

        @classmethod
        def from_line_raw(cls, line_raw: str) -> "TransactionImporterTDCanadaPDF.TransactionRowParser":
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
            trx_counter = TransactionImporterTDCanadaPDF.transactions_counter
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
        def from_line_raw(cls, line_raw: str) -> "TransactionImporterTDCanadaPDF.DocumentDateRowParser":
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

    def process(self) -> None:
        transactions: list["Transaction"] = []
        texts: list[str] = []
        field_values: dict = {}
        year: Optional[int] = None
        for line in self.iter_file():
            if self.TransactionRowParser.is_match(line_raw=line):
                trx_parser = self.TransactionRowParser.from_line_raw(line_raw=line)
                trx_date, transaction_id_raw, transaction_id, amount = trx_parser.parse(year=year)
                field_values = dict(
                    account_id=self.account.pk,
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

        # Determine transactions to-add vs to-update
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

    def iter_file(self) -> Iterator[str]:
        pdf = pdfium.PdfDocument(self.source)
        for page in pdf:
            lines: list[str] = page.get_textpage().get_text_range().split("\n")
            yield from lines


class TransactionImporterTDCanadaCSV(Importer):

    class RowRaw(TypedDict):
        date: str
        transaction_id_raw: str
        amount_out: str
        amount_in: str
        current_balance: str

    class TransactionRowParser:
        parent: "TransactionImporterTDCanadaCSV"
        row_raw: "TransactionImporterTDCanadaCSV.RowRaw"
        row_number: int

        def __init__(
            self,
            parent: "TransactionImporterTDCanadaCSV",
            row_raw: "TransactionImporterTDCanadaCSV.RowRaw",
            row_number: int,
        ) -> None:
            self.parent = parent
            self.row_number = row_number
            self.row_raw = row_raw

        def parse(self) -> tuple[str, str, date, Decimal]:
            # Parse date
            date_raw = self.row_raw["date"]
            date = datetime.strptime(date_raw, "%m/%d/%Y").date()
            # Parse transaction_id
            transaction_id_raw: str = self.row_raw["transaction_id_raw"]
            trx_count: str = self.parent.transactions_counter.get(
                transaction_id_raw,
                0,
            )
            transaction_id: str = f"{transaction_id_raw}:{date}:{trx_count}"
            self.parent.transactions_counter[transaction_id_raw] += 1
            # Parse amount
            amount_in: Optional[str] = self.row_raw["amount_in"] or None
            amount_out: Optional[str] = self.row_raw["amount_out"] or None
            if amount_in is None and amount_out is None:
                raise ValidationError(
                    f"Either amount_in or amount_out must be defined [line:{self.row_number}]"
                )
            if amount_in is not None and amount_out is not None:
                raise ValidationError(
                    f"amount_in or amount_out is mutually exclusive [line:{self.row_number}]"
                )
            sign = -1 if amount_out is not None else 1
            amount = sign * Decimal(amount_in or amount_out)
            # Return parsed values
            return transaction_id_raw, transaction_id, date, amount

    def process(self) -> None:
        field_values: dict = {}
        transactions: list[Transaction] = []
        for i, row in enumerate(self.iter_file()):
            row_parser = self.TransactionRowParser(
                parent=self, 
                row_raw=row, 
                row_number=i,
            )
            trx_id_raw, trx_id, date, amount = row_parser.parse()
            field_values = dict(
                    account_id=self.account.pk,
                    date=date,
                    transaction_id_raw=trx_id_raw,
                    transaction_id=trx_id,
                    amount=amount,
                )
            trx = Transaction(**field_values)
            transactions.append(trx)
        
        # Determine transactions to-add vs to-update
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
        Transaction.objects.bulk_update(
            transactions_to_update, 
            fields=tuple(field_values.keys()),
        )
        logger.info("Bulk-created %s new transactions", len(transactions_new))
        logger.info("Bulk-updated %s existing transactions", len(transactions_to_update))

    def iter_file(self) -> Iterator["RowRaw"]:
        with open(self.source, "r") as csv_file:
            csv_reader = csv.DictReader(
                csv_file, 
                fieldnames=[
                    "date", 
                    "transaction_id_raw", 
                    "amount_out",
                    "amount_in",
                    "current_balance",
                ],
            )
            for row in csv_reader:
                yield row


class TransactionImporterKOHOCSV(Importer):
    ZERO_STR = "0.00"  # KOHO uses this value to indicate null amount in/out

    class RowRaw(TypedDict):
        date_time: str
        transaction_id_raw: str
        amount_in: str
        amount_out: str
        current_balance: str
        notes: str

    class TransactionRowParser:
        parent: "TransactionImporterKOHOCSV"
        row_raw: "TransactionImporterKOHOCSV.RowRaw"
        row_number: int

        def __init__(
            self,
            parent: "TransactionImporterKOHOCSV",
            row_raw: "TransactionImporterKOHOCSV.RowRaw",
            row_number: int,
        ) -> None:
            self.parent = parent
            self.row_number = row_number
            self.row_raw = row_raw

        def parse(self) -> tuple[str, str, date, Decimal]:
            # Parse date
            date_time_raw, _ = self.row_raw["date_time"].split(" ", maxsplit=1)
            date = datetime.strptime(date_time_raw, "%Y-%m-%d").date()
            # Parse transaction_id
            transaction_id_raw: str = self.row_raw["transaction_id_raw"]
            trx_count: str = self.parent.transactions_counter.get(
                transaction_id_raw,
                0,
            )
            transaction_id: str = f"{transaction_id_raw}:{date}:{trx_count}"
            self.parent.transactions_counter[transaction_id_raw] += 1
            # Parse amount
            null = self.parent.ZERO_STR
            amount_in: str = self.row_raw["amount_in"] or null
            amount_out: str = self.row_raw["amount_out"] or null
            if amount_in == null and amount_out == null:
                logger.debug(
                    "Row %s is just a status update transaction for '%s' [Note: %s]",
                    self.row_number, 
                    self.row_raw["transaction_id_raw"], 
                    self.row_raw["notes"],
                )
            if amount_in != null and amount_out != null:
                raise ValidationError(
                    f"amount_in or amount_out is mutually exclusive [line:{self.row_number}]"
                )
            sign = -1 if amount_out != null else 1
            amount = sign * Decimal(amount_in if amount_in != null else amount_out)
            # Return parsed values
            return transaction_id_raw, transaction_id, date, amount

    def process(self) -> None:
        field_values: dict = {}
        transactions: list[Transaction] = []
        for i, row in enumerate(self.iter_file()):
            if i == 0:
                # Skip header row
                continue
            row_parser = self.TransactionRowParser(
                parent=self, 
                row_raw=row, 
                row_number=i,
            )
            trx_id_raw, trx_id, date, amount = row_parser.parse()
            field_values = dict(
                    account_id=self.account.pk,
                    date=date,
                    transaction_id_raw=trx_id_raw,
                    transaction_id=trx_id,
                    amount=amount,
                )
            trx = Transaction(**field_values)
            transactions.append(trx)

        if not transactions:
            logger.info("Input file has no transactions - Nothing to do.")
            return
        
        # Determine transactions to-add vs to-update
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
        Transaction.objects.bulk_update(
            transactions_to_update, 
            fields=tuple(field_values.keys()),
        )
        logger.info("Bulk-created %s new transactions", len(transactions_new))
        logger.info("Bulk-updated %s existing transactions", len(transactions_to_update))

    def iter_file(self) -> Iterator["RowRaw"]:
        with open(self.source, "r") as csv_file:
            csv_reader = csv.DictReader(
                csv_file,
                fieldnames=[
                    "date_time", 
                    "transaction_id_raw", 
                    "amount_in",
                    "amount_out",
                    "current_balance",
                    "notes",
                ],
            )
            for i, row in enumerate(csv_reader):
                yield row
