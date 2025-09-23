import json
import os
from datetime import datetime
from typing import Dict, List, Optional, TypedDict
from dataclasses import dataclass, asdict

# Define data models
@dataclass
class Product:
    id: int
    name: str
    price: float
    unit: str  # e.g., 'liter', 'packet', 'bottle'
    stock: float = 0
    date_added: str = datetime.now().strftime("%Y-%m-%d %H:%M")

@dataclass
class Client:
    id: int
    name: str
    phone: str
    date_added: str = datetime.now().strftime("%Y-%m-%d %H:%M")

@dataclass
class Supplier:
    id: int
    name: str
    phone: str
    date_added: str = datetime.now().strftime("%Y-%m-%d %H:%M")

@dataclass
class SaleItem:
    product_id: int
    quantity: float
    price_per_unit: float
    total: float

@dataclass
class Sale:
    id: int
    client_id: int
    items: List[SaleItem]
    total_amount: float
    date: str

@dataclass
class Delivery:
    id: int
    supplier_id: int
    product_id: int
    quantity: float
    price_per_unit: float
    total_cost: float
    date: str

# Data storage file
DATA_FILE = "milk_bar_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Convert dicts back to objects
            return data
    return {
        "products": [],
        "clients": [],
        "suppliers": [],
        "sales": [],
        "deliveries": []
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else o)

def add_product():
    data = load_data()
    print("\n=== Add New Product ===")
    product = Product(
        id=len(data["products"]) + 1,
        name=input("Product Name: "),
        price=float(input("Price per unit (Ksh): ")),
        unit=input("Unit (e.g., liter, packet, bottle): "),
        stock=float(input("Initial stock quantity: ") or 0)
    )
    data["products"].append(product.__dict__)
    save_data(data)
    print(f"Product '{product.name}' added successfully!")

def add_client():
    data = load_data()
    print("\n=== Add New Client ===")
    client = Client(
        id=len(data["clients"]) + 1,
        name=input("Client Name: "),
        phone=input("Phone: ")
    )
    data["clients"].append(client.__dict__)
    save_data(data)
    print(f"Client '{client.name}' added successfully!")

def add_supplier():
    data = load_data()
    print("\n=== Add New Supplier ===")
    supplier = Supplier(
        id=len(data["suppliers"]) + 1,
        name=input("Supplier Name: "),
        phone=input("Phone: ")
    )
    data["suppliers"].append(supplier.__dict__)
    save_data(data)
    print(f"Supplier '{supplier.name}' added successfully!")

def record_sale():
    data = load_data()
    print("\n=== Record New Sale ===")
    
    # Show available products
    if not data["products"]:
        print("No products available. Please add products first.")
        return
        
    print("\nAvailable Products:")
    for product in data["products"]:
        print(f"ID: {product['id']} - {product['name']} ({product['stock']} {product['unit']}s in stock) - Ksh {product['price']}/{product['unit']}")
    
    client_id = int(input("\nClient ID: "))
    sale_items = []
    total_amount = 0
    
    while True:
        try:
            product_id = int(input("\nProduct ID (or 0 to finish): "))
            if product_id == 0:
                break
                
            product = next((p for p in data["products"] if p['id'] == product_id), None)
            if not product:
                print("Invalid product ID. Please try again.")
                continue
                
            quantity = float(input(f"Quantity ({product['unit']}s): "))
            if quantity > product['stock']:
                print(f"Not enough stock! Only {product['stock']} {product['unit']}s available.")
                continue
                
            price_per_unit = product['price']
            item_total = quantity * price_per_unit
            
            sale_items.append({
                'product_id': product_id,
                'quantity': quantity,
                'price_per_unit': price_per_unit,
                'total': item_total
            })
            
            total_amount += item_total
            
            # Update product stock
            product['stock'] -= quantity
            
            print(f"Added {quantity} {product['unit']}(s) of {product['name']} - Ksh {item_total:.2f}")
            print(f"Current total: Ksh {total_amount:.2f}")
            
        except ValueError:
            print("Invalid input. Please enter a valid number.")
            continue
    
    if not sale_items:
        print("No items added to sale.")
        return
    
    # Record the sale
    sale = {
        'id': len(data["sales"]) + 1,
        'client_id': client_id,
        'items': sale_items,
        'total_amount': total_amount,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    data["sales"].append(sale)
    save_data(data)
    
    # Print receipt
    print("\n=== SALE RECEIPT ===")
    print(f"Sale ID: {sale['id']}")
    print(f"Date: {sale['date']}")
    print("-" * 30)
    for item in sale_items:
        product = next(p for p in data["products"] if p['id'] == item['product_id'])
        print(f"{product['name']}: {item['quantity']} {product['unit']}s x Ksh {item['price_per_unit']:.2f} = Ksh {item['total']:.2f}")
    print("-" * 30)
    print(f"TOTAL: Ksh {total_amount:.2f}")
    print("=" * 30)
    print("Thank you for your business!")

def record_delivery():
    data = load_data()
    print("\n=== Record New Delivery ===")
    
    # Show available suppliers
    if not data["suppliers"]:
        print("No suppliers available. Please add a supplier first.")
        return
        
    print("\nAvailable Suppliers:")
    for supplier in data["suppliers"]:
        print(f"ID: {supplier['id']} - {supplier['name']} ({supplier['phone']})")
    
    # Show available products
    if not data["products"]:
        print("No products available. Please add products first.")
        return
        
    print("\nAvailable Products:")
    for product in data["products"]:
        print(f"ID: {product['id']} - {product['name']} ({product['stock']} {product['unit']}s in stock)")
    
    try:
        supplier_id = int(input("\nSupplier ID: "))
        product_id = int(input("Product ID: "))
        quantity = float(input("Quantity: "))
        price_per_unit = float(input("Price per unit (Ksh): "))
        
        total_cost = quantity * price_per_unit
        
        delivery = {
            'id': len(data["deliveries"]) + 1,
            'supplier_id': supplier_id,
            'product_id': product_id,
            'quantity': quantity,
            'price_per_unit': price_per_unit,
            'total_cost': total_cost,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        # Update product stock
        product = next((p for p in data["products"] if p['id'] == product_id), None)
        if product:
            product['stock'] += quantity
        
        data["deliveries"].append(delivery)
        save_data(data)
        
        print(f"\nDelivery recorded successfully!")
        print(f"Added {quantity} {product['unit']}s of {product['name']}")
        print(f"Total Cost: Ksh {total_cost:.2f}")
        
    except ValueError:
        print("Invalid input. Please enter valid numbers.")
        return

def get_client_name(client_id: int, data: Dict) -> str:
    for client in data["clients"]:
        if client["id"] == client_id:
            return client["name"]
    return "Unknown"

def get_supplier_name(supplier_id: int, data: Dict) -> str:
    for supplier in data["suppliers"]:
        if supplier["id"] == supplier_id:
            return supplier["name"]
    return "Unknown"

def get_product_name(product_id: int, data: Dict) -> str:
    for product in data["products"]:
        if product["id"] == product_id:
            return product["name"]
    return "Unknown"

def view_client_transactions():
    data = load_data()
    client_id = int(input("Enter Client ID: "))
    
    client_sales = [s for s in data["sales"] if s["client_id"] == client_id]
    
    if not client_sales:
        print("No transactions found for this client.")
        return
    
    client_name = get_client_name(client_id, data)
    print(f"\n=== Transaction History for {client_name} ===")
    print("Date                 | Liters | Price/Liter | Total")
    print("-" * 50)
    
    for sale in sorted(client_sales, key=lambda x: x["date"], reverse=True):
        print(f"{sale['date']} | {sale['liters']:6.2f} | {sale['price_per_liter']:11.2f} | {sale['total']:8.2f}")

def search_records():
    data = load_data()
    print("\n=== Search Records ===")
    print("1. Search Sales by Date")
    print("2. Search Deliveries by Date")
    print("3. Back to Main Menu")
    
    choice = input("Enter your choice (1-3): ")
    
    if choice == "1":
        date = input("Enter date (YYYY-MM-DD) or press Enter for all sales: ")
        print("\n=== Sales Records ===")
        print("Date                 | Client          | Liters | Price/Liter | Total")
        print("-" * 70)
        
        for sale in data["sales"]:
            if not date or sale["date"].startswith(date):
                client_name = get_client_name(sale["client_id"], data)
                print(f"{sale['date']} | {client_name:15} | {sale['liters']:6.2f} | {sale['price_per_liter']:11.2f} | {sale['total']:8.2f}")
    
    elif choice == "2":
        date = input("Enter date (YYYY-MM-DD) or press Enter for all deliveries: ")
        print("\n=== Delivery Records ===")
        print("Date                 | Supplier        | Liters | Price/Liter | Total")
        print("-" * 70)
        
        for delivery in data["deliveries"]:
            if not date or delivery["date"].startswith(date):
                supplier_name = get_supplier_name(delivery["supplier_id"], data)
                print(f"{delivery['date']} | {supplier_name:15} | {delivery['liters']:6.2f} | {delivery['price_per_liter']:11.2f} | {delivery['total_cost']:8.2f}")

def view_products():
    data = load_data()
    print("\n=== Product Inventory ===")
    if not data["products"]:
        print("No products available.")
        return
        
    print("ID  | Name                | Price/Unit  | Stock   | Unit")
    print("-" * 60)
    for product in data["products"]:
        print(f"{product['id']:3d} | {product['name'][:18]:18} | Ksh {product['price']:7.2f} | {product['stock']:7.2f} | {product['unit']}")

def view_summary():
    data = load_data()
    print("\n=== Business Summary ===")
    print(f"Total Products: {len(data['products'])}")
    print(f"Total Clients: {len(data['clients'])}")
    print(f"Total Suppliers: {len(data['suppliers'])}")
    
    # Calculate total sales
    total_sales = sum(sale['total_amount'] for sale in data["sales"])
    total_deliveries = sum(delivery['total_cost'] for delivery in data["deliveries"])
    
    # Calculate total quantities sold by product
    product_sales = {}
    for sale in data["sales"]:
        for item in sale['items']:
            product_id = item['product_id']
            if product_id not in product_sales:
                product_sales[product_id] = 0
            product_sales[product_id] += item['quantity']
    
    print(f"\n=== Financial Summary ===")
    print(f"Total Sales (Ksh): {total_sales:,.2f}")
    print(f"Total Delivery Costs (Ksh): {total_deliveries:,.2f}")
    print(f"Profit (Ksh): {total_sales - total_deliveries:,.2f}")
    
    if product_sales:
        print("\n=== Sales by Product ===")
        for product_id, quantity in product_sales.items():
            product = next((p for p in data["products"] if p['id'] == product_id), None)
            if product:
                print(f"{product['name']}: {quantity:.2f} {product['unit']}s")
    
    # Top clients
    if data["sales"]:
        client_totals = {}
        for sale in data["sales"]:
            client_id = sale["client_id"]
            client_totals[client_id] = client_totals.get(client_id, 0) + sale["total_amount"]
        
        if client_totals:
            print("\n=== Top Clients ===")
            for client_id, total in sorted(client_totals.items(), key=lambda x: x[1], reverse=True)[:3]:
                client_name = next((c['name'] for c in data['clients'] if c['id'] == client_id), 'Unknown')
                print(f"{client_name}: Ksh {total:,.2f}")

def main_menu():
    while True:
        print("\n=== Mama's Milk Bar Management System ===")
        print("1. Add New Product")
        print("2. Add New Client")
        print("3. Add New Supplier")
        print("4. Record Sale")
        print("5. Record Delivery")
        print("6. View Products")
        print("7. View Business Summary")
        print("8. View Client Transactions")
        print("9. Search Records")
        print("10. Exit")
        
        choice = input("\nEnter your choice (1-10): ")
        
        if choice == "1":
            add_product()
        elif choice == "2":
            add_client()
        elif choice == "3":
            add_supplier()
        elif choice == "4":
            record_sale()
        elif choice == "5":
            record_delivery()
        elif choice == "6":
            view_products()
        elif choice == "7":
            view_summary()
        elif choice == "8":
            view_client_transactions()
        elif choice == "9":
            search_records()
        elif choice == "10":
            print("Thank you for using Mama's Milk Bar Management System!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
