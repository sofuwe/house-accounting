import logging

from django.core.management.base import BaseCommand

from householdentities.services import EntityService
from importing.services import MappingReadService
from market_data.services import MarketDataReadService, MarketDataWriteService
from transactions.services import TransactionWriteService, TransactionMappingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Maps transactions to vendors"

    def handle(self, *args, **options):
        market_data_rd_svc = MarketDataReadService()
        market_data_write_svc = MarketDataWriteService()
        mapping_rd_svc = MappingReadService()
        trx_write_svc = TransactionWriteService(
            entity_service=EntityService(),
        )
        trx_mapping_wr_svc = TransactionMappingService(
            mapping_rd_svc=mapping_rd_svc,
            market_data_rd_svc=market_data_rd_svc,
            market_data_wr_svc=market_data_write_svc,
            trx_wr_svc=trx_write_svc,
        )

        trx_mapping_wr_svc.map_transactions_to_vendors()
