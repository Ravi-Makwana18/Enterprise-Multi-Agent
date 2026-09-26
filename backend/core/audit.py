import logging
from typing import Any

from backend.core.pii import redact_pii

logger = logging.getLogger("audit")


def log_audit(action: str, user: str | None, role: str | None, **details: Any) -> None:
    payload = {
        "event": action,
        "user": user,
        "role": role,
        "details": {
            key: redact_pii(str(value)) if isinstance(value, str) else value
            for key, value in details.items()
        },
    }
    logger.info("audit_event", extra={"context": payload})
