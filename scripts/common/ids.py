from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = uuid4().hex[:10].upper()
    return f"{prefix}-{date}-{suffix}"
