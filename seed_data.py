import json
import os
from datetime import datetime

DATA_FILE = "milk_bar_data.json"

SAMPLE_PRODUCTS = [
    {"id": 1, "name": "Fresh Milk", "price": 60.0, "unit": "liter", "stock": 100.0, "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")},
    {"id": 2, "name": "Mala", "price": 50.0, "unit": "packet", "stock": 60.0, "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")},
    {"id": 3, "name": "Yogurt", "price": 80.0, "unit": "bottle", "stock": 40.0, "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")},
]

SAMPLE_SUPPLIERS = [
    {"id": 1, "name": "KCC Dairies", "phone": "0700000001", "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")},
    {"id": 2, "name": "Brookside Dairies", "phone": "0700000002", "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")},
]

SAMPLE_CLIENTS = [
    {"id": 3, "name": "Jane Doe", "phone": "0711222333", "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")},
    {"id": 4, "name": "Kamau", "phone": "0700111222", "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")},
]

SAMPLE_DELIVERIES = [
    # supplier 1 delivers product 1 and 2
    {"supplier_id": 1, "product_id": 1, "quantity": 50.0, "price_per_unit": 45.0},
    {"supplier_id": 1, "product_id": 2, "quantity": 30.0, "price_per_unit": 40.0},
    # supplier 2 delivers product 3
    {"supplier_id": 2, "product_id": 3, "quantity": 20.0, "price_per_unit": 60.0},
]

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"products": [], "clients": [], "suppliers": [], "sales": [], "deliveries": []}


def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def ensure_ids(items, start_at=1, key="id"):
    max_id = max([it.get(key, 0) for it in items], default=0)
    cur = max(max_id, start_at - 1)
    for it in items:
        if key not in it:
            cur += 1
            it[key] = cur
    return items


def main():
    data = load()

    # Ensure keys exist
    for k in ["products", "clients", "suppliers", "sales", "deliveries"]:
        data.setdefault(k, [])

    # Seed products if missing
    if not data["products"]:
        data["products"] = SAMPLE_PRODUCTS.copy()
    else:
        # add missing sample products by name if not existing
        existing_names = {p["name"].lower() for p in data["products"]}
        next_id = max([p.get("id", 0) for p in data["products"]], default=0)
        for p in SAMPLE_PRODUCTS:
            if p["name"].lower() not in existing_names:
                next_id += 1
                p = p.copy()
                p["id"] = next_id
                data["products"].append(p)

    # Seed suppliers
    if not data["suppliers"]:
        data["suppliers"] = SAMPLE_SUPPLIERS.copy()
    else:
        existing_names = {s["name"].lower() for s in data["suppliers"]}
        next_id = max([s.get("id", 0) for s in data["suppliers"]], default=0)
        for s in SAMPLE_SUPPLIERS:
            if s["name"].lower() not in existing_names:
                next_id += 1
                s = s.copy()
                s["id"] = next_id
                data["suppliers"].append(s)

    # Seed clients (add only new ones)
    existing_client_names = {c["name"].lower() for c in data["clients"]}
    next_id = max([c.get("id", 0) for c in data["clients"]], default=0)
    for c in SAMPLE_CLIENTS:
        if c["name"].lower() not in existing_client_names:
            next_id += 1
            c = c.copy()
            c["id"] = next_id
            data["clients"].append(c)

    # Add a few deliveries and update stock
    next_delivery_id = max([d.get("id", 0) for d in data["deliveries"]], default=0)
    for d in SAMPLE_DELIVERIES:
        next_delivery_id += 1
        total_cost = d["quantity"] * d["price_per_unit"]
        delivery = {
            "id": next_delivery_id,
            "supplier_id": d["supplier_id"],
            "product_id": d["product_id"],
            "quantity": d["quantity"],
            "price_per_unit": d["price_per_unit"],
            "total_cost": total_cost,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        data["deliveries"].append(delivery)
        # update product stock
        for p in data["products"]:
            if p["id"] == d["product_id"]:
                p["stock"] = float(p.get("stock", 0)) + float(d["quantity"])  # additive
                break

    save(data)
    print("Seeding complete. Products, suppliers, clients, and sample deliveries added.")


if __name__ == "__main__":
    main()
