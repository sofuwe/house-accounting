from enum import StrEnum
from typing import Protocol

from entities.interfaces import TransactionInstitutionSource


class ITransactionImporter(Protocol):
    source: str
    institution: TransactionInstitutionSource

    def process(self) -> None:
        ...
