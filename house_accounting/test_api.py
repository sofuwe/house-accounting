import datetime as dt
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from market_data.services import MarketDataService
import pytest

from charts.services import ChartsReadService
from householdentities.services import EntityService
from transactions.services import TransactionReadService


@pytest.mark.django_db
def test_current_balances():
    entity_service = EntityService()
    chart_service = ChartsReadService(
        transaction_service=TransactionReadService(),
        entity_service=entity_service,
    )

    value_over_dates_before_actual = chart_service.get_value_over_dates(
        accounts=[123],
        date_fr=dt.date(2020, 1, 1),
        date_to=dt.date(2020, 1, 5),
    )

    value_over_dates_before_expected = [
        (0, Decimal("0.0")),  # 2020-01-01
        (1, Decimal("0.0")),  # 2020-01-02
        (2, Decimal("0.0")),  # 2020-01-03
        (3, Decimal("0.0")),  # 2020-01-04
        (4, Decimal("0.0")),  # 2020-01-05
    ]
    assert value_over_dates_before_actual == value_over_dates_before_expected

    call_command(
        "import_data",
        *("--source-dir", str(Path(__file__).parent / "test-input-data-0")),
    )

    value_over_dates_after_actual = chart_service.get_value_over_dates(
        accounts=[-123],  # Non-existing account
        date_fr=dt.date(2020, 1, 1),
        date_to=dt.date(2020, 1, 5),
    )
    value_over_dates_after_expected = [
        (0, Decimal("0.0")),  # 2020-01-01
        (1, Decimal("0.0")),  # 2020-01-02
        (2, Decimal("0.0")),  # 2020-01-03
        (3, Decimal("0.0")),  # 2020-01-04
        (4, Decimal("0.0")),  # 2020-01-05
    ]
    assert value_over_dates_after_actual == value_over_dates_after_expected

    value_over_dates_after_proper_accounts_actual = chart_service.get_value_over_dates(
        accounts=entity_service.get_all_account_ids(),
        date_fr=dt.date(2020, 1, 1),
        date_to=dt.date(2020, 1, 5),
    )

    value_over_dates_after_proper_accounts_expected = [
        (0, Decimal("-63.3700")),  # 2020-01-01: -50.04 (trx) + -13.33 (trx)
        (1, Decimal("36.6300")),  # 2020-01-02: +100.0 (trx)
        (2, Decimal("36.6300")),  # 2020-01-03: +0.0 (no trx)
        (3, Decimal("36.6300")),  # 2020-01-04: +0.0 (no trx)
        (4, Decimal("1036.6300")),  # 2020-01-05: +1000.0 (Account initial amount)
    ]
    print(value_over_dates_after_proper_accounts_actual)
    assert value_over_dates_after_proper_accounts_actual == value_over_dates_after_proper_accounts_expected


@pytest.mark.django_db
def test_bds_campaign_contribution():
    entity_service = EntityService()
    chart_service = ChartsReadService(
        transaction_service=TransactionReadService(),
        entity_service=entity_service,
        market_data_service=MarketDataService()
    )

    call_command(
        "import_data",
        *("--source-dir", str(Path(__file__).parent / "test-input-data-0")),
    )
    call_command(
        "track",
        *("--date-fr", "2020-01-01"),
        *("--date-to", "2020-01-05"),
    )

    contribution_bds_actual = chart_service.get_contribution_bds_as_of(
        accounts=entity_service.get_all_account_ids(),
        date_as_of=dt.date(2020, 1, 5),
    )

    contribution_bds_expected = {
        "labels": [
            "BDS High Priority",
            "BDS Medium Priority",
            "BDS Low Priority",
            "BDS No Boycott",
        ],
        "values": [
            Decimal("0.01"),
            Decimal("0.04"),
            Decimal("0.15"),
            Decimal("0.8"), 
        ],
        "total": Decimal("1.0"),
    }
    assert contribution_bds_actual == contribution_bds_expected
