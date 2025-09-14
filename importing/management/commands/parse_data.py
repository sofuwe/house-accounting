from ast import Not
import datetime as dt
import decimal
from email.policy import default
import logging
from collections import defaultdict
from pathlib import Path
from typing import Protocol

from django.core.management.base import BaseCommand
import pydantic

from householdentities.models import Account, Institution
from importing.parsers import AccountCSVFileRowStandard, TransactionCSVRowStandard
from importing.services import ParserService
from importing.validators.parsing import ImportDirParserValidator

logger = logging.getLogger(__name__)


class InvalidParseDirStructure(Exception):
    """Custom exception for invalid directory structure errors."""


class ITransactionRowParsed(Protocol):
    account_id: str
    date: dt.date

    @property
    def columns(self) -> list[str]:
        """Return the list of model field names in a particular order."""
        raise NotImplementedError


class IAccountRowParsed(Protocol):
    name: str
    amount_initial: decimal.Decimal
    date_start: dt.date


class Command(BaseCommand):
    help = "Validate and parse transaction files from source directory, then save to a destination directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            type=str,
            help="Path to the import data directory.",
        )
        parser.add_argument(
            "--dest-dir",
            type=str,
            help="Path to the destination directory to copy parsed files to.",
        )

    def handle(self, *args, **options):
        source_dir = Path(options["source_dir"])
        logger.info("Validating import data directory: %s", source_dir)
        self._validate(source_dir)

        logger.info("Import data directory is valid, proceed with parsing")
        dest_dir = Path(options["dest_dir"])
        self._parse_and_save(source_dir, dest_dir)

    def _validate(self, source_dir: Path) -> None:
        dir_validator = ImportDirParserValidator(source_dir)
        err_msg = dir_validator.is_valid()
        if err_msg:
            raise InvalidParseDirStructure(err_msg)

    def _parse_and_save(self, source_dir: Path, dest_dir: Path) -> None:
        # TODO @imranariffin: Simplify this command, and move this parsing logic to a service class.

        parser_service = ParserService(source_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        trx_rows_map: dict[str, list[TransactionCSVRowStandard]] = defaultdict(list)
        account_ids_map: dict[str, set[str]] = defaultdict(set)
        acc_earliest_trx_date_map: dict[str, dt.date] = {}
        acc_by_file_name_map: dict[str, str] = {}

        for institution, account_id, parsed in parser_service.iter_parsed_transactions():
            month: str = parsed.date.strftime("%Y-%m")
            dest_file_name = f"{institution.value}__{account_id}__{month}.csv"
            trx_rows_map[dest_file_name].append(parsed)
            account_ids_map[institution].add(account_id)
            acc_by_file_name_map[dest_file_name] = account_id

        # Save parsed transactions to "Transactions/" folder:

        dest_dir_trx = dest_dir / "Transactions"
        dest_dir_trx.mkdir(exist_ok=True)

        for dest_file_name, rows in trx_rows_map.items():
            dest_file = dest_dir_trx / dest_file_name

            # columns: list[str] = rows[0].columns
            columns: list[str] = parser_service.to_standard_csv_columns(rows[0])
            with dest_file.open("w", encoding="utf-8") as fo:
                fo.write(",".join(columns) + "\n")
                for row in rows:
                    # values = []
                    # for col in columns:
                    #     value = str(getattr(row, col))
                    #     if "," in value or '"' in value:
                    #         value = '"' + value.replace("\"", "\"\"") + '"'
                    #     values.append(value)

                    # fo.write(",".join(values) + "\n")
                    line_csv = parser_service.to_standard_csv(row)
                    fo.write(line_csv + "\n")

                    account_id = acc_by_file_name_map[dest_file_name]
                    if (
                        account_id not in acc_earliest_trx_date_map
                        or row.date < acc_earliest_trx_date_map[account_id]
                    ):
                        acc_earliest_trx_date_map[account_id] = row.date

            logger.info("Saved %s parsed transactions to file: %s", len(rows), dest_file)

        # Save parsed accounts to "Accounts.csv" file:

        dest_file_accounts = dest_dir / "Accounts.csv"

        # If available from source directory, collect accounts from there first
        account_data_map: dict[str, dict[str, AccountCSVFileRowStandard]] = defaultdict(dict)
        for parsed in parser_service.iter_parsed_accounts():
            account_data_map[parsed.institution][parsed.account_id] = parsed

        with dest_file_accounts.open("w", encoding="utf-8") as fo:
            fo.write("AccountID,Name,Institution,AmountInitial,DateStart\n")
            for institution, acc_ids in account_ids_map.items():
                account_data_map_ = account_data_map.get(institution, {})
                for acc_id in sorted(acc_ids):
                    earliest_trx_date = acc_earliest_trx_date_map[account_id]
                    account_info = account_data_map_.get(acc_id)
                    account_name = account_info.name if account_info and account_info.name else '""'
                    amount_initial = (
                        account_info.amount_initial
                        if account_info and account_info.amount_initial is not None
                        else decimal.Decimal("0.0")
                    )
                    account_row = (
                        f"{acc_id},{account_name},{institution},{amount_initial},{earliest_trx_date}\n"
                    )
                    fo.write(account_row)
            logger.info("Saved %s parsed accounts to file: %s", len(account_ids_map), dest_file_accounts)

        # TODO @imranariffin: Extract AmountInitial from files if "Current Balance" is included
        #   Else, default to a special string .e.g "N/A"
