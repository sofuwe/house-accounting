import logging
import os

from django.core.management.base import BaseCommand

from typing import TYPE_CHECKING

from ...services import Importer
from ...interfaces import TransactionInstitutionSource

if TYPE_CHECKING:  # pragma: no cover
    from typing import Any, Optional

    from django.core.management.base import CommandParser

    from ...interfaces import ITransactionImporter

logger = logging.getLogger(__name__)


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
        institution: TransactionInstitutionSource = TransactionInstitutionSource[
            options["institution"]
        ]
        if os.path.isfile(source):
            self._import_from_file(source=source, institution=institution)
        else:
            self._import_from_directory(source_dir=source, institution=institution)

    def _import_from_file(
        self, 
        source: str, 
        institution: TransactionInstitutionSource,
    ) -> None:
        logger.info("Import from file %s", source)
        importer: "ITransactionImporter" = Importer.from_args(
            source=source,
            institution=institution,
        )
        importer.process()

    def _import_from_directory(
        self,
        source_dir: str,
        institution: TransactionInstitutionSource,
    ) -> None:
        for source_file_or_dir in os.listdir(source_dir):
            source_file_or_dir: str = os.path.join(
                source_dir,
                source_file_or_dir,
            )
            if os.path.isdir(source_file_or_dir):
                logger.info("Skip %s since it is a directory", source_file_or_dir)
                continue

            source_file = source_file_or_dir
            logger.info("Import from file %s", source_file)
            importer = Importer.from_args(
                source=source_file,
                institution=institution,
            )
            importer.process()
