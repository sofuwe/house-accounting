import datetime as dt


DATE_FIRST = dt.date(1950, 1, 1)
DATE_LAST = dt.date(2099, 12, 31)
DATES_LIST: list[dt.date] = [
    DATE_FIRST + dt.timedelta(days=i)
    for i in range((DATE_LAST - DATE_FIRST).days + 1)
]
DATES_INDEX: dict[dt.date, int] = {
    date_value: i for i, date_value in enumerate(DATES_LIST)
}

def get_dates(date_fr: dt.date, date_to: dt.date) -> list[dt.date]:
    date_fr_i = DATES_INDEX[date_fr]
    date_to_i = DATES_INDEX[date_to]
    return DATES_LIST[date_fr_i: date_to_i + 1]
