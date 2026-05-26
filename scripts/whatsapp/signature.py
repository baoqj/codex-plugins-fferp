from __future__ import annotations

import hashlib
import hmac


def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str | None) -> bool:
    """Verify Meta's X-Hub-Signature-256 when an app secret is configured."""
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
