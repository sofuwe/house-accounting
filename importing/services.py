import decimal
import enum
from pathlib import Path
from typing import Iterator
from venv import logger

from importing.models import VendorTransactionIdMap
from importing.parsers import (
    AccountCSVFileRowStandard,
    AccountFileParserStandard,
    TransactionCSVFileParserKOHO,
    TransactionCSVFileParserTDCanada,
    TransactionFilesParserStandard,
    TransactionCSVRowStandard,
)


class InstitutionName(enum.StrEnum):
    koho = "KOHO"
    td_canada = "TDCanada"


class ParserService:
    def __init__(self, dir_path: Path):
        self.dir_path = dir_path

    def iter_parsed_transactions(self) -> Iterator[tuple[InstitutionName, str, TransactionCSVRowStandard]]:
        for dir_path in self.dir_path.glob("*"):
            if not dir_path.is_dir():
                logger.debug("Skipping non-directory path: %s", dir_path)
                continue

            dir_name: str = dir_path.name
            if "__" not in dir_name:
                logger.warning("Skipping directory with invalid name: %s", dir_name)
                continue

            institution: InstitutionName = InstitutionName(dir_name.split("__")[0])
            acc_natural_key: str = dir_name.split("__")[1]

            match institution:
                case InstitutionName.td_canada:
                    parser_class = TransactionCSVFileParserTDCanada
                case InstitutionName.koho:
                    parser_class = TransactionCSVFileParserKOHO
                case _:
                    logger.warning("Skipping unsupported institution: %s", institution)
                    continue

            for trx_file in dir_path.glob("*.csv"):
                parser = parser_class(trx_file)
                for parsed in parser.iter_parsed():
                    yield institution, acc_natural_key, parsed

    def iter_parsed_accounts(self) -> Iterator[AccountCSVFileRowStandard]:
        acc_file = self.dir_path / "Accounts.csv"
        if not acc_file.is_file():
            logger.debug("Accounts.csv file not found in directory: %s, skipping", self.dir_path)
            return

        parser = AccountFileParserStandard(acc_file)
        for parsed in parser.iter_parsed():
            yield parsed

    def to_standard_csv(
        self,
        row: TransactionCSVRowStandard | AccountCSVFileRowStandard,
    ) -> str:
        # TODO @imranariffin: Replace with .model_dump_csv()
        return ",".join(f'"{str(v)}"' if "," in str(v) else str(v) for v in row.model_dump().values())

    def to_standard_csv_columns(
        self, row: TransactionCSVRowStandard | AccountCSVFileRowStandard
    ) -> list[str]:
        aliases = [
            field.serialization_alias or field.alias
            for field in row.__class__.model_fields.values()
            if field.alias or field.serialization_alias
        ]
        assert len(aliases) == len(row.__class__.model_fields), (
            "All fields must have aliases "
            f"[fields: {[field for field in row.__class__.model_fields.values() if not (field.alias or field.serialization_alias)]}]"
        )
        return aliases


class MappingService:

    def get_trx_to_vendor_map(self) -> dict[str, str]:
        return dict(
            VendorTransactionIdMap.objects.all()
            .values_list("transaction_id_raw", "vendor_id"),
        )
