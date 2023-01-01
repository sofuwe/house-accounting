from enum import StrEnum
from typing import Protocol


class TransactionInstitutionSource(StrEnum):
    td_canada = "TD_CANADA"
    koho = "KOHO"


class ITransactionImporter(Protocol):
    source: str
    institution: TransactionInstitutionSource

    def process(self) -> None:
        ...
