from __future__ import annotations

import csv

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.db import connect


MASTER_FILES = {
    "products.csv": ["product_id", "sku", "product_name", "aliases", "unit", "wholesale_price", "active"],
    "customers.csv": ["customer_id", "customer_name", "whatsapp_number", "region", "customer_level", "active"],
    "suppliers.csv": ["supplier_id", "supplier_name", "contact_person", "phone", "active"],
    "distributors.csv": ["distributor_id", "name", "whatsapp_number", "region", "level", "active"],
    "warehouses.csv": ["warehouse_id", "warehouse_name", "address", "active"],
    "price_rules.csv": ["rule_id", "customer_level", "sku", "discount_rate", "min_quantity", "active"],
}

TRANSACTION_FILES = {
    "sales_orders.csv": ["order_id", "customer_id", "order_date", "status", "source_message_id", "total_amount"],
    "purchase_orders.csv": ["purchase_order_id", "supplier_id", "order_date", "status", "total_amount"],
    "inventory_movements.csv": ["movement_id", "date", "sku", "warehouse_id", "movement_type", "quantity"],
    "payments.csv": ["payment_id", "customer_id", "order_id", "payment_date", "amount", "status"],
    "receivables.csv": ["receivable_id", "customer_id", "order_id", "amount_due", "amount_paid", "due_date", "status"],
}


def _write_csv_if_missing(path, headers):
    if path.exists():
        return False
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
    return True


def main() -> None:
    settings = ensure_runtime_dirs(get_settings())
    created = []
    for filename, headers in MASTER_FILES.items():
        if _write_csv_if_missing(settings.data_dir / "master" / filename, headers):
            created.append(filename)
    for filename, headers in TRANSACTION_FILES.items():
        if _write_csv_if_missing(settings.data_dir / "transactions" / filename, headers):
            created.append(filename)
    connect(settings.database_path).close()
    if created:
        print("Created starter files:", ", ".join(created))
    else:
        print("Starter files already exist.")


if __name__ == "__main__":
    main()
