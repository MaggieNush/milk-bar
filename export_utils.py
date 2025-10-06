import os
import pandas as pd
from typing import Dict, List


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def export_all_csv(data: Dict, out_dir: str = "exports"):
    """
    Export all key entities to CSVs:
    - products.csv
    - clients.csv
    - suppliers.csv
    - deliveries.csv (with supplier/product names)
    - sales.csv (one row per sale item, with client/product names)
    """
    _ensure_dir(out_dir)

    # Basic tables
    pd.DataFrame(data.get("products", [])).to_csv(os.path.join(out_dir, "products.csv"), index=False)
    pd.DataFrame(data.get("clients", [])).to_csv(os.path.join(out_dir, "clients.csv"), index=False)
    pd.DataFrame(data.get("suppliers", [])).to_csv(os.path.join(out_dir, "suppliers.csv"), index=False)

    # Helper lookups
    clients = {c.get("id"): c.get("name") for c in data.get("clients", [])}
    suppliers = {s.get("id"): s.get("name") for s in data.get("suppliers", [])}
    products = {p.get("id"): p.get("name") for p in data.get("products", [])}

    # Deliveries, enriched
    deliveries_rows: List[Dict] = []
    for d in data.get("deliveries", []):
        deliveries_rows.append({
            "id": d.get("id"),
            "date": d.get("date"),
            "supplier_id": d.get("supplier_id"),
            "supplier": suppliers.get(d.get("supplier_id"), "Unknown"),
            "product_id": d.get("product_id"),
            "product": products.get(d.get("product_id"), "Unknown"),
            "quantity": d.get("quantity", d.get("liters")),
            "price_per_unit": d.get("price_per_unit", d.get("price_per_liter")),
            "total_cost": d.get("total_cost")
        })
    pd.DataFrame(deliveries_rows).to_csv(os.path.join(out_dir, "deliveries.csv"), index=False)

    # Sales flattened to line items
    sales_rows: List[Dict] = []
    for s in data.get("sales", []):
        items = s.get("items")
        if items:
            for it in items:
                sales_rows.append({
                    "sale_id": s.get("id"),
                    "date": s.get("date"),
                    "client_id": s.get("client_id"),
                    "client": clients.get(s.get("client_id"), "Unknown"),
                    "product_id": it.get("product_id"),
                    "product": products.get(it.get("product_id"), "Unknown"),
                    "quantity": it.get("quantity"),
                    "price_per_unit": it.get("price_per_unit"),
                    "line_total": it.get("total"),
                    "sale_total": s.get("total_amount")
                })
        else:
            # legacy single-line milk sale
            sales_rows.append({
                "sale_id": s.get("id"),
                "date": s.get("date"),
                "client_id": s.get("client_id"),
                "client": clients.get(s.get("client_id"), "Unknown"),
                "product_id": None,
                "product": "Milk (legacy)",
                "quantity": s.get("liters"),
                "price_per_unit": s.get("price_per_liter"),
                "line_total": s.get("total"),
                "sale_total": s.get("total")
            })
    pd.DataFrame(sales_rows).to_csv(os.path.join(out_dir, "sales.csv"), index=False)
