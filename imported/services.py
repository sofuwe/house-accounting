from dis import Instruction
from typing import TYPE_CHECKING

from .interfaces import TransactionInstitutionSource
from .models import Transaction

if TYPE_CHECKING:  # pragma: no cover
    from .interfaces import ITransactionImporter


class Importer:
    def from_args(source: str, institution: "TransactionInstitutionSource") -> "ITransactionImporter":
        if institution == TransactionInstitutionSource.td_canada.value:
            return TransactionImporterTDCanada(source=source, institution=institution)
        raise Exception(
            f"source:institution combination {source}:{institution.value} not supported."
        )


class TransactionImporterTDCanada(Importer):

    def __init__(self, source: str, institution: "TransactionInstitutionSource") -> None:
        self.source = source
        self.institution = Instruction

    def process(self) -> None:
        transactions: list["Transaction"] = []

        with open(self.source, mode="rb") as f:
            print(f.read())

        Transaction.objects.bulk_create(transactions)
