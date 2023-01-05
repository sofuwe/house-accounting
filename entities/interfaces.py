from enum import StrEnum


class TransactionInstitutionSource(StrEnum):
    td_canada = "TD_CANADA"
    koho = "KOHO"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(x.name, x.value) for x in cls]
