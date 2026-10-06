"""Input validators (§23) — CPF check digits, masked display, HH:MM format."""

import re


def _check_digit(plate: str, start_weight: int) -> int:
    total = sum(int(n) * w for n, w in zip(plate, range(start_weight, 1, -1)))
    return (total * 10) % 11 % 10


def cpf_valid(cpf: str) -> bool:
    digits = re.sub(r"\D", "", cpf or "")
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    v1 = _check_digit(digits[:9], 10)
    v2 = _check_digit(digits[:10], 11)
    return digits[9:] == f"{v1}{v2}"


def cpf_digits(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def cpf_masked(cpf: str) -> str:
    """Sensitive-data display rule (§7): never show the full CPF where it is not required."""
    digits = cpf_digits(cpf)
    if len(digits) != 11:
        return "***"
    return f"***.{digits[3:6]}.***-{digits[9:]}"


def hhmm_valid(value: str) -> bool:
    if not re.fullmatch(r"\d{2}:\d{2}", value or ""):
        return False
    hours, minutes = value.split(":")
    return int(hours) <= 23 and int(minutes) <= 59
