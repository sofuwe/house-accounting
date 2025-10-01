import logging

from django.core.management.base import BaseCommand

from householdentities.services import EntityService
from importing.services import MappingService
from market_data.services import MarketDataReadService, MarketDataWriteService
from transactions.services import TransactionWriteService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Maps transactions to vendors"

    def handle(self, *args, **options):
        market_data_rd_srv = MarketDataReadService()
        market_data_write_svc = MarketDataWriteService()
        mapping_srv = MappingService()
        trx_write_svc = TransactionWriteService(
            entity_service=EntityService(),
        )

        trx_to_vendor_map = mapping_srv.get_trx_to_vendor_map()

        vendors_to_create: list[tuple[str, str]] = []
        vendor_id_map = market_data_rd_srv.get_vendor_id_map()
        for vendor_id in trx_to_vendor_map.values():
            if vendor_id not in vendor_id_map:
                vendors_to_create.append((vendor_id, vendor_id))
    
        vendors_created, _ = market_data_write_svc.bulk_create_or_update_vendors(
            vendors_to_create,
        )
        logger.debug("Created %s new vendors", vendors_created)

        count: int = trx_write_svc.map_transactions_to_vendors(
            trx_to_vendor_map=trx_to_vendor_map,
            vendor_id_map=market_data_rd_srv.get_vendor_id_map(),
        )
        logger.debug("Mapped %s transactions to vendors", count)
