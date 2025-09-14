import datetime as dt
import decimal
from gettext import install
import logging
from pathlib import Path
from typing import Iterator, Protocol

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from config.services import ConfigWriteService
from householdentities.services import EntityService
from transactions.services import TransactionReadService, TransactionWriteService
from importing.parsers import (
    AccountFileParserStandard,
    TransactionFilesParserStandard,
)
from importing.validators.importing import (
    ImportDirValidator,
    AccountFileValidator,
    ImportTransactionDirValidator,
)

logger = logging.getLogger(__name__)


class InvalidImportDirStructure(Exception):
    """Custom exception for invalid directory structure errors."""


class IAccountParsed(Protocol):
    account_id: str
    name: str
    institution: str
    amount_initial: decimal.Decimal
    date_start: dt.date


class ITransactionParsed(Protocol):
    date: dt.date
    account_id: str
    transaction_id: str
    transaction_id_raw: str
    amount: decimal.Decimal


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--source-dir",
            required=True,
            type=str,
            help=(
                "The source directory to import data from. Source directory structure: \n"
                "<--source-dir>/\n"
                "├── Accounts.csv\n"
                "└── Transactions/\n"
                "    ├── <Account-AccountID>_<YYYY>-<mm>-<dd>.csv\n"
                "    ├── ...\n"
                "    └── <Account-AccountID>_<YYYY>-<mm>-<dd>.csv\n"
            ),
        )

    def handle(self, **options) -> str | None:
        source_dir = Path(options["source_dir"])
        # Validate the input
        self._validate(source_dir)
        # Continue with the import process
        logger.info("Directory structure and file formats are valid, proceed with import")
        self._import(source_dir)

    def _validate(self, source_dir: Path) -> None:
        dir_validator = ImportDirValidator(source_dir)
        err_msg = dir_validator.is_valid()
        if err_msg:
            raise InvalidImportDirStructure(err_msg)

        acc_file_validator = AccountFileValidator(source_dir)
        err_msg = acc_file_validator.is_valid()
        if err_msg:
            raise InvalidImportDirStructure(err_msg)

        # TODO @imranariffin: Add AccountTransactionValidator that validates:
        # 1. Each transaction file name matches the expected pattern
        # 2. Each transaction file's account natural ID exists in Accounts.csv
        # 3. Each transaction date is not before the account's start date

        trx_dir_validator = ImportTransactionDirValidator(source_dir)
        err_msg = trx_dir_validator.is_valid()
        if err_msg:
            raise InvalidImportDirStructure(err_msg)

    def _import(self, source_dir: Path) -> None:
        acc_parser = AccountFileParserStandard(source_dir / "Accounts.csv")
        accounts: Iterator[IAccountParsed] = acc_parser.iter_parsed()
        entity_service = EntityService()
        created, updated = entity_service.bulk_create_or_update_accounts(accounts)
        logger.info("Imported accounts [created: %s, updated: %s]", created, updated)

        trx_parser = TransactionFilesParserStandard(source_dir / "Transactions")
        transactions: Iterator[ITransactionParsed] = trx_parser.iter_parsed()
        trx_service = TransactionWriteService(entity_service=entity_service)
        created, updated = trx_service.bulk_create_or_update_transactions(transactions)
        logger.info("Imported transactions [created: %s, updated: %s]", created, updated)

        config_service = ConfigWriteService(
            entity_service=entity_service,
            transaction_service=TransactionReadService(),
        )
        date_fr, date_to = config_service.get_earliest_latest_date()
        if date_fr and date_to:
            created = config_service.update_or_create_latest_config(date_fr=date_fr, date_to=date_to)
            logger.info(
                "%s config [date_fr=%s, date_to=%s]",
                *("Created" if created else "Updated", date_fr, date_to),
            )
