from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentResult:
    intent: str
    risk_level: str
    confidence: float


KEYWORDS = {
    "complaint": ["complaint", "broken", "bad quality", "refund", "compensation", "投诉", "坏了", "质量", "退款", "赔偿"],
    "payment_notice": ["paid", "payment", "transfer", "receipt", "bank", "付款", "转账", "收据", "已付"],
    "delivery_status": ["delivery", "ship", "shipped", "arrive", "tracking", "送货", "发货", "到货", "物流"],
    "order_confirmation": ["confirm order", "confirmed", "确认订单", "确认下单"],
    "order_request": ["order", "buy", "need", "want", "qty", "pcs", "case", "下单", "订", "要", "箱", "件"],
    "quotation_request": ["quote", "quotation", "price", "pricing", "discount", "报价", "价格", "多少钱", "折扣"],
    "after_sales": ["return", "exchange", "warranty", "after sales", "退换", "售后", "保修"],
    "inquiry": ["hello", "hi", "available", "stock", "catalog", "你好", "在吗", "库存", "目录", "有货"],
}

RISK_LEVEL = {
    "inquiry": "low",
    "quotation_request": "medium",
    "order_request": "medium",
    "order_confirmation": "high",
    "delivery_status": "medium",
    "payment_notice": "high",
    "complaint": "high",
    "after_sales": "high",
    "unknown": "medium",
}


def classify_intent(text: str | None) -> IntentResult:
    normalized = (text or "").lower()
    if not normalized.strip():
        return IntentResult("unknown", "medium", 0.0)

    best_intent = "unknown"
    best_hits = 0
    for intent, keywords in KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword.lower() in normalized)
        if hits > best_hits:
            best_hits = hits
            best_intent = intent

    if best_intent == "unknown":
        return IntentResult("unknown", RISK_LEVEL["unknown"], 0.35)
    confidence = min(0.55 + best_hits * 0.2, 0.95)
    return IntentResult(best_intent, RISK_LEVEL[best_intent], confidence)
