import re

_EMAIL_PATTERN = re.compile(r"(?P<user>[A-Za-z0-9._%+-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_PHONE_PATTERN = re.compile(r"\b(?P<area>\d{3})-(?P<mid>\d{3})-(?P<last>\d{4})\b")
_AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_PASSPORT_PATTERN = re.compile(r"\b[A-Z]\d{7}\b")


def redact_email(match: re.Match[str]) -> str:
    domain = match.group("domain")
    return f"***@{domain}"


def redact_phone(match: re.Match[str]) -> str:
    return f"***-***-{match.group('last')}"


def redact_aadhaar(match: re.Match[str]) -> str:
    return "************"


def redact_passport(match: re.Match[str]) -> str:
    return "********"


def redact_pii(value: str) -> str:
    if not value:
        return value

    text = _EMAIL_PATTERN.sub(redact_email, value)
    text = _PHONE_PATTERN.sub(redact_phone, text)
    text = _AADHAAR_PATTERN.sub(redact_aadhaar, text)
    text = _PASSPORT_PATTERN.sub(redact_passport, text)
    return text
