import datetime as dt


from dataclasses import dataclass
from typing import Protocol

from config.models import Config
from householdentities.services import EntityService
from transactions.services import TransactionReadService


@dataclass
class ConfigBasic:
    date_fr: dt.date | None
    date_to: dt.date | None


class IConfigIn(Protocol):
    date_fr: dt.date
    date_to: dt.date


class ConfigWriteService:
    def __init__(self, entity_service: EntityService, transaction_service: TransactionReadService):
        self._entity_service = entity_service
        self._trx_service = transaction_service

    def get_earliest_latest_date(self) -> tuple[dt.date | None, dt.date | None]:
        earliest_trx, latest_trx = self._trx_service.get_earliest_latest_date()
        earliest_acc = self._entity_service.get_earliest_account_start_date()
        if earliest_trx is None:
            return earliest_acc, latest_trx
        if earliest_acc is None:
            return earliest_trx, latest_trx
        return min(earliest_trx, earliest_acc), latest_trx

    def update_or_create_latest_config(self, date_fr: dt.date, date_to: dt.date) -> bool:
        """
        Update the latest config or create a new one if it doesn't exist.

        :param config_update: The new config values to update or create.
        :return: True if a new config was created, False if an existing config was updated.
        """
        config = Config.objects.order_by("-created_at").first()
        if config:
            config.date_fr = date_fr
            config.date_to = date_to
            config.save(update_fields=["date_fr", "date_to"])
            return False
        else:
            Config.objects.create(
                date_fr=date_fr,
                date_to=date_to,
            )
            return True


class ConfigReadService:
    def get_latest_config(self) -> ConfigBasic | None:
        config = Config.objects.order_by("-created_at").first()
        if config:
            return ConfigBasic(
                date_fr=config.date_fr,
                date_to=config.date_to,
            )
        return None
