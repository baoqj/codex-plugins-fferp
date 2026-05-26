from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.ids import utc_now_iso


def append_jsonl(log_name: str, record: dict[str, Any], data_dir: Path | None = None) -> Path:
    settings = ensure_runtime_dirs(get_settings())
    base_dir = data_dir or settings.data_dir
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / log_name
    payload = {"timestamp": utc_now_iso(), **record}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return path
