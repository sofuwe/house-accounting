from django.core.management.base import BaseCommand

from typing import TYPE_CHECKING

from ...services import Importer
from ...interfaces import TransactionInstitutionSource

if TYPE_CHECKING:  # pragma: no cover
    from typing import Any, Optional

    from django.core.management.base import CommandParser

    from ...interfaces import ITransactionImporter


class Command(BaseCommand):
    """
    Import transactions from a file of transactions.
    
    Supported file formats:
    * PDF

    Supported institution from which transactions are sourced:
    * TD Bank Canada
    """

    def add_arguments(self, parser: "CommandParser") -> None:
        parser.add_argument(
            "--source", 
            help="Path to transaction file to source from",
            required=True,
        )
        parser.add_argument(
            "--institution",
            help="Institution the transaction file is from",
            type=str,
            required=True,
            choices=[x.name for x in TransactionInstitutionSource],
        )

    def handle(self, *args: "Any", **options: "Any") -> "Optional[str]":
        source: str = options["source"]
        institution: TransactionInstitutionSource = TransactionInstitutionSource[options["institution"]]
        importer: "ITransactionImporter" = Importer.from_args(
            source=source,
            institution=institution,
    )
        importer.process()
