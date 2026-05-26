from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    plugin_root: Path
    data_dir: Path
    output_dir: Path
    database_url: str | None
    database_path: Path
    api_token: str | None
    approval_mode: str
    auto_reply_low_risk: bool
    whatsapp_send_enabled: bool
    whatsapp_verify_token: str | None
    whatsapp_access_token: str | None
    whatsapp_phone_number_id: str | None
    whatsapp_business_account_id: str | None
    whatsapp_app_secret: str | None
    whatsapp_graph_api_version: str


def get_settings() -> Settings:
    data_dir = Path(os.getenv("FFERP_DATA_DIR", PLUGIN_ROOT / "data")).expanduser()
    output_dir = Path(os.getenv("FFERP_OUTPUT_DIR", PLUGIN_ROOT / "output")).expanduser()
    if not data_dir.is_absolute():
        data_dir = PLUGIN_ROOT / data_dir
    if not output_dir.is_absolute():
        output_dir = PLUGIN_ROOT / output_dir

    return Settings(
        plugin_root=PLUGIN_ROOT,
        data_dir=data_dir,
        output_dir=output_dir,
        database_url=os.getenv("DATABASE_URL"),
        database_path=data_dir / "database" / "fferp.sqlite",
        api_token=os.getenv("FFERP_API_TOKEN"),
        approval_mode=os.getenv("FFERP_APPROVAL_MODE", "manual"),
        auto_reply_low_risk=_bool_env("FFERP_AUTO_REPLY_LOW_RISK", False),
        whatsapp_send_enabled=_bool_env("FFERP_WHATSAPP_SEND_ENABLED", False),
        whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN"),
        whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN"),
        whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
        whatsapp_business_account_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID"),
        whatsapp_app_secret=os.getenv("WHATSAPP_APP_SECRET"),
        whatsapp_graph_api_version=os.getenv("WHATSAPP_GRAPH_API_VERSION", "v25.0"),
    )


def ensure_runtime_dirs(settings: Settings | None = None) -> Settings:
    settings = settings or get_settings()
    for path in (
        settings.data_dir / "inbox",
        settings.data_dir / "master",
        settings.data_dir / "transactions",
        settings.data_dir / "database",
        settings.data_dir / "logs",
        settings.output_dir / "approvals",
        settings.output_dir / "drafts" / "whatsapp",
        settings.output_dir / "drafts" / "orders",
        settings.output_dir / "drafts" / "delivery",
        settings.output_dir / "reports",
    ):
        path.mkdir(parents=True, exist_ok=True)
    return settings
