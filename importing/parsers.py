from ast import parse
import csv
import datetime as dt
import decimal
import hashlib
import logging
from pathlib import Path
from typing import Annotated, Generic, Iterator, TypeVar

from pydantic import BaseModel, Field
import smart_open


logger = logging.getLogger(__name__)


class ParsingErrorRow(Exception):
    """Custom exception for errors during parsing of a row."""


class RowInBase(BaseModel):
    @classmethod
    def columns(cls) -> list[str]:
        """Return the list of model field names in a particular order."""
        return [
            str(field.validation_alias or "") or field.serialization_alias or field.alias or name
            for name, field in cls.model_fields.items()
        ]

    # TODO @imranariffin: Define model_dump_csv() to dump model as CSV row string


T = TypeVar("T", bound=RowInBase)
V = TypeVar("V", bound=BaseModel)


class FileParserCSVBase(Generic[T, V]):
    RowIn: type[T]
    RowOut: type[V]

    def __init__(self, path: Path) -> None:
        self.path = path

    def parse_row(self, row_in: T, file_path: Path, row_num: int) -> V:
        """Parse a single row from RowIn to RowOut."""
        raise NotImplementedError("Subclasses must implement parse_row method.")

    def iter_parsed(self) -> Iterator[V]:
        if self.path.is_file():
            yield from self.iter_parsed_file(self.path)
        else:
            for file_path in self.path.glob("*.csv"):
                yield from self.iter_parsed_file(file_path)

    def iter_parsed_file(self, file_path: Path) -> Iterator[V]:
        logger.debug("Parsing file: %s", file_path)
        with smart_open.open(file_path, "r") as file:
            reader = csv.DictReader(file, fieldnames=self.RowIn.columns())
            row: dict[str, str]
            for i, row_ in enumerate(reader):
                # Strip whitespace from all values in the row
                try:
                    row = {k: v.strip() if isinstance(v, str) else v for k, v in row_.items()}
                except Exception as e:
                    raise

                # Skip header row if present
                curr_values = set(row.values())
                columns_expected = set(self.RowIn.columns())
                if len(curr_values & columns_expected) == len(columns_expected):
                    logger.debug("[%s] First row is a header, skipping it", self.path)
                    continue

                # Inject useful metadata into each row
                row["row_num"] = str(i)
                row["path"] = str(file_path)

                try:
                    row_parsed = self.parse_row(self.RowIn.model_validate(row), file_path, i)
                    yield row_parsed
                except Exception as e:
                    logger.error("Error parsing row %s in file %s [error: %s, row: %s]", i, file_path, e, row)
                    raise e


class AccountCSVFileRowStandard(BaseModel):
    account_id: Annotated[str, Field(serialization_alias="AccountID")]
    name: Annotated[str, Field(serialization_alias="Name")]
    institution: Annotated[str, Field(serialization_alias="Institution")]
    amount_initial: Annotated[decimal.Decimal, Field(serialization_alias="AmountInitial")]
    date_start: Annotated[dt.date, Field(serialization_alias="DateStart")]


class AccountCSVFileRowInStandard(RowInBase):
    account_id: Annotated[str, Field(validation_alias="AccountID")]
    name: Annotated[str, Field(validation_alias="Name")]
    institution: Annotated[str, Field(validation_alias="Institution")]
    amount_initial: Annotated[str, Field(validation_alias="AmountInitial")]
    date_start: Annotated[str, Field(validation_alias="DateStart")]


class AccountFileParserStandard(FileParserCSVBase[AccountCSVFileRowInStandard, AccountCSVFileRowStandard]):
    RowIn = AccountCSVFileRowInStandard
    RowOut = AccountCSVFileRowStandard

    def parse_row(
        self, row_in: AccountCSVFileRowInStandard, file_path: Path, row_num: int
    ) -> AccountCSVFileRowStandard:
        row_out = AccountCSVFileRowStandard(**row_in.model_dump())
        return AccountCSVFileRowStandard.model_validate(row_out)


class TransactionCSVRowStandard(BaseModel):
    date: Annotated[dt.date, Field(serialization_alias="Date")]
    account_id: Annotated[str, Field(serialization_alias="AccountID")]
    transaction_id: Annotated[str, Field(serialization_alias="TransactionID")]
    transaction_id_raw: Annotated[str, Field(serialization_alias="TransactionIDRaw")]
    amount: Annotated[decimal.Decimal, Field(serialization_alias="Amount")]


class TransactionCSVRowInTDCanada(RowInBase):
    Date: str
    TransactionID: str
    AmountOut: str
    AmountIn: str
    # TODO @imranariffin: Use Balance to calculate AmountInitial for account if needed
    Balance: str


class TransactionCSVFileParserTDCanada(
    FileParserCSVBase[TransactionCSVRowInTDCanada, TransactionCSVRowStandard]
):
    RowIn = TransactionCSVRowInTDCanada
    RowOut = TransactionCSVRowStandard

    def parse_row(
        self, row_in: TransactionCSVRowInTDCanada, file_path: Path, row_num: int
    ) -> TransactionCSVRowStandard:
        try:
            trx_date = dt.datetime.strptime(row_in.Date, "%m/%d/%Y").date()
        except ValueError:
            trx_date = dt.datetime.strptime(row_in.Date, "%Y-%m-%d").date()

        trx_id_ = row_in.TransactionID.strip().replace(" ", "")
        trx_id_hash = hashlib.md5(f"{trx_id_}-{row_in.Date}-{row_num}".encode()).hexdigest()[:10]
        trx_id = f"{trx_id_}-{trx_id_hash}"

        row_out = self.RowOut(
            date=trx_date,
            account_id=Path(file_path).parent.name.split("__")[1],
            transaction_id=trx_id,
            transaction_id_raw=row_in.TransactionID,
            amount=decimal.Decimal(row_in.AmountIn or 0) - decimal.Decimal(row_in.AmountOut or 0),
        )
        return self.RowOut.model_validate(row_out)


class TransactionCSVRowInKOHO(RowInBase):
    Date: str
    Transaction: str
    Loads: str
    Withdrawal: str
    Balance: str
    Notes: str


class TransactionCSVFileParserKOHO(FileParserCSVBase[TransactionCSVRowInKOHO, TransactionCSVRowStandard]):
    RowIn = TransactionCSVRowInKOHO
    RowOut = TransactionCSVRowStandard

    def parse_row(
        self, row_in: TransactionCSVRowInKOHO, file_path: Path, row_num: int
    ) -> TransactionCSVRowStandard:
        # Split date and time, only keep date part
        trx_date = dt.datetime.strptime(row_in.Date.split(" ", maxsplit=1)[0], "%Y-%m-%d").date()

        trx_id_ = row_in.Transaction.strip().replace(" ", "")
        trx_id_hash = hashlib.md5(f"{trx_id_}-{row_in.Date}-{row_num}".encode()).hexdigest()[:10]
        trx_id = f"{trx_id_}-{trx_id_hash}"

        amount_out_str = row_in.Withdrawal.strip().replace(",", "")
        amount_in_str = row_in.Loads.strip().replace(",", "")
        assert amount_in_str or amount_out_str, "Either Withdrawal or Loads must be present"

        try:
            amount_out_str = amount_out_str if amount_out_str else None
        except Exception:
            raise ParsingErrorRow(f"Row {row_num}: Invalid AmountOut value: {amount_out_str}")
        try:
            amount_in_str = amount_in_str if amount_in_str else None
        except Exception:
            raise ParsingErrorRow(f"Row {row_num}: Invalid AmountIn value: {amount_in_str}")

        amount = decimal.Decimal(amount_in_str or 0) - decimal.Decimal(amount_out_str or 0)

        row_out = self.RowOut(
            date=trx_date,
            account_id=Path(file_path).parent.name.split("__")[1],
            transaction_id=trx_id,
            transaction_id_raw=row_in.Transaction,
            amount=amount,
        )
        return self.RowOut.model_validate(row_out)


class TransactionCSVRowInStandard(RowInBase):
    date: Annotated[dt.date, Field(validation_alias="Date")]
    account_id: Annotated[str, Field(validation_alias="AccountID")]
    transaction_id: Annotated[str, Field(validation_alias="TransactionID")]
    transaction_id_raw: Annotated[str, Field(validation_alias="TransactionIDRaw")]
    amount: Annotated[decimal.Decimal, Field(validation_alias="Amount")]


class TransactionFilesParserStandard(
    FileParserCSVBase[TransactionCSVRowInStandard, TransactionCSVRowStandard]
):
    RowIn = TransactionCSVRowInStandard
    RowOut = TransactionCSVRowStandard

    def parse_row(
        self, row_in: TransactionCSVRowInStandard, file_path: Path, row_num: int
    ) -> TransactionCSVRowStandard:
        row_out = self.RowOut(**row_in.model_dump())
        return self.RowOut.model_validate(row_out)
