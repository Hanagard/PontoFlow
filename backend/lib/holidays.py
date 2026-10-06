"""Brazilian national holidays (§ feriados) — computed, not hardcoded per year.

Fixed-date holidays plus the Easter-derived movable ones (Carnaval, Paixão de Cristo,
Corpus Christi) via the anonymous Gregorian computus. Municipal/estadual holidays are
registered manually by each company.
"""

from datetime import date, timedelta

FIXED = [
    ((1, 1), "Confraternização Universal"),
    ((4, 21), "Tiradentes"),
    ((5, 1), "Dia do Trabalho"),
    ((9, 7), "Independência do Brasil"),
    ((10, 12), "Nossa Senhora Aparecida"),
    ((11, 2), "Finados"),
    ((11, 15), "Proclamação da República"),
    ((11, 20), "Consciência Negra"),
    ((12, 25), "Natal"),
]


def easter(year: int) -> date:
    """Anonymous Gregorian computus — Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    lunar = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lunar) // 451
    month = (h + lunar - 7 * m + 114) // 31
    day = ((h + lunar - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def national_holidays(year: int) -> list[dict]:
    """[{date: 'YYYY-MM-DD', name, kind}] for the given year, sorted by date."""
    easter_sunday = easter(year)
    items = [{"date": date(year, m, d).isoformat(), "name": name, "kind": "nacional"} for (m, d), name in FIXED]
    items += [
        {"date": (easter_sunday - timedelta(days=48)).isoformat(), "name": "Carnaval", "kind": "facultativo"},
        {"date": (easter_sunday - timedelta(days=47)).isoformat(), "name": "Carnaval", "kind": "facultativo"},
        {"date": (easter_sunday - timedelta(days=2)).isoformat(), "name": "Paixão de Cristo", "kind": "nacional"},
        {"date": (easter_sunday + timedelta(days=60)).isoformat(), "name": "Corpus Christi", "kind": "facultativo"},
    ]
    return sorted(items, key=lambda h: h["date"])
