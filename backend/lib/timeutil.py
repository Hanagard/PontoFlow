"""Server-side time helpers.

The official timestamp of every punch is produced HERE (aware UTC on write); the company
timezone is applied only on presentation and for local-day grouping. The browser clock is
never trusted for anything (§9).
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "America/Belem"


def now_utc() -> datetime:
    """Aware UTC now — the only clock the backend trusts."""
    return datetime.now(timezone.utc)


def tzinfo_for(tz: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz or DEFAULT_TZ)
    except Exception:
        return ZoneInfo(DEFAULT_TZ)


def local_date_of(dt: datetime, tz: str | None) -> date:
    """Local calendar date of an (aware) instant in the company timezone."""
    return dt.astimezone(tzinfo_for(tz)).date()


def local_today(tz: str | None) -> date:
    return local_date_of(now_utc(), tz)


def local_dt(day: date, hhmm: str, tz: str | None) -> datetime:
    """Aware UTC instant for a local wall-clock date + "HH:MM" in the company timezone."""
    total = parse_hhmm(hhmm)
    local = datetime.combine(day, time(total // 60, total % 60), tzinfo=tzinfo_for(tz))
    return local.astimezone(timezone.utc)


def day_bounds_utc(day: date, tz: str | None) -> tuple[datetime, datetime]:
    """[start, end) of a local calendar day as aware UTC datetimes — the Mongo query range."""
    z = tzinfo_for(tz)
    start_local = datetime.combine(day, time.min, tzinfo=z)
    return start_local.astimezone(timezone.utc), (start_local + timedelta(days=1)).astimezone(timezone.utc)


def date_range_utc(start: date, end: date, tz: str | None) -> tuple[datetime, datetime]:
    start_utc, _ = day_bounds_utc(start, tz)
    _, end_utc = day_bounds_utc(end, tz)
    return start_utc, end_utc


def parse_hhmm(value: str) -> int:
    """'08:30' -> 510 minutes. Raises ValueError on malformed input."""
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def hhmm(minutes: int | None) -> str | None:
    """510 -> '08:30'; negative values are prefixed (saldo negativo)."""
    if minutes is None:
        return None
    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)
    return f"{sign}{minutes // 60:02d}:{minutes % 60:02d}"


def hhmm_of(dt: datetime, tz: str | None) -> str:
    return dt.astimezone(tzinfo_for(tz)).strftime("%H:%M")
