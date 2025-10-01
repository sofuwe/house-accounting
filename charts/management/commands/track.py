import datetime as dt
import logging

from django.core.management.base import BaseCommand, CommandParser

from charts.services import ChartsWriteService
from householdentities.services import EntityService
from transactions.services import TransactionReadService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Track and store metric values for accounts."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--date-fr", type=str, help="Start date for tracking (YYYY-MM-DD)")
        parser.add_argument("--date-to", type=str, help="End date for tracking (YYYY-MM-DD)")

    def handle(self, *args, **options):

        entity_service = EntityService()        
        charts_wr_service = ChartsWriteService(
            entity_service=entity_service,
            txn_rd_service=TransactionReadService(),
        )

        date_fr: dt.date = dt.datetime.strptime(options["date_fr"], "%Y-%m-%d").date()
        date_to: dt.date = dt.datetime.strptime(options["date_to"], "%Y-%m-%d").date()

        account_earliest_date: dt.date | None = entity_service.get_earliest_account_start_date()
        if account_earliest_date is None:
            logger.error("No valid account start date found. Skipping tracking.")
            return

        if date_fr < account_earliest_date:
            logger.error(
                "Start date (%s) is earlier than the earliest account start date (%s). Skipping tracking.",
                date_fr,
                account_earliest_date,
            )
            return

        logger.info("Tracking accounts from %s to %s ...", date_fr, date_to)

        charts_wr_service.track_accounts(
            accounts=entity_service.get_all_account_ids(),
            date_fr=date_fr,
            date_to=date_to,
        )
