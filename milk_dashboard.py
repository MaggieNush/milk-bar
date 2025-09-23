import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from milk_bar import load_data, get_client_name, get_supplier_name, get_product_name

# Set page config
st.set_page_config(
    page_title="Mama's Milk Bar Dashboard",
    page_icon="🥛",
    layout="wide"
)

# Helper functions
def load():
    return load_data()

def save(data):
    with open("milk_bar_data.json", 'w') as f:
        json.dump(data, f, indent=2)

# Load data
data = load()

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Sales", "Clients", "Suppliers", "Products"])

# Helper functions
def format_currency(amount):
    return f"Ksh {amount:,.2f}"

def get_client_options(d):
    return {f"{c['name']} (ID {c['id']})": c['id'] for c in d.get('clients', [])}

def get_product_options(d):
    return {f"{p['name']} - Ksh {p['price']}/{p['unit']} (Stock: {p['stock']})": p['id'] for p in d.get('products', [])}

# Dashboard Page
if page == "Dashboard":
    st.title("🥛 Mama's Milk Bar Dashboard")
    
    # Calculate metrics
    total_sales = sum(sale.get("total_amount", 0) for sale in data.get("sales", []))
    total_deliveries = sum(delivery["total_cost"] for delivery in data["deliveries"])
    profit = total_sales - total_deliveries
    total_clients = len(data["clients"])
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Sales", format_currency(total_sales))
    with col2:
        st.metric("Total Expenses", format_currency(total_deliveries))
    with col3:
        st.metric("Profit", format_currency(profit))
    with col4:
        st.metric("Total Clients", total_clients)
    
    # Recent Sales
    st.subheader("Recent Sales")
    if data.get("sales"):
        recent_sales = sorted(data["sales"], key=lambda x: x["date"], reverse=True)[:5]
        sales_rows = []
        for sale in recent_sales:
            client_name = get_client_name(sale["client_id"], data)
            items_summary = ", ".join([
                f"{get_product_name(it['product_id'], data)} x{it['quantity']}" for it in sale.get("items", [])
            ])
            sales_rows.append({
                "Date": sale["date"],
                "Client": client_name,
                "Items": items_summary,
                "Total": sale.get("total_amount", 0)
            })
        st.dataframe(pd.DataFrame(sales_rows), use_container_width=True)
    else:
        st.info("No sales recorded yet." )
    
    # Recent Deliveries
    st.subheader("Recent Deliveries")
    if data["deliveries"]:
        recent_deliveries = sorted(data["deliveries"], key=lambda x: x["date"], reverse=True)[:5]
        delivery_data = []
        for delivery in recent_deliveries:
            delivery_data.append({
                "Date": delivery["date"],
                "Supplier": get_supplier_name(delivery["supplier_id"], data),
                "Quantity": delivery.get("quantity", 0),
                "Price/Unit": delivery.get("price_per_unit", 0),
                "Total": delivery.get("total_cost", 0)
            })
        st.dataframe(pd.DataFrame(delivery_data), use_container_width=True)
    else:
        st.info("No deliveries recorded yet.")

# Sales Page
elif page == "Sales":
    st.title("📊 Sales Overview & Record Sale")

    # Record New Sale
    st.subheader("Record New Sale")
    if "cart" not in st.session_state:
        st.session_state.cart = []
    data = load()  # refresh data in case of changes

    if not data.get("products"):
        st.warning("No products available. Please add products first using the CLI or Products page.")
    elif not data.get("clients"):
        st.warning("No clients available. Please add clients first on the Clients page.")
    else:
        with st.form("add_to_cart", clear_on_submit=True):
            client_map = get_client_options(data)
            client_label = st.selectbox("Client", options=list(client_map.keys()))
            product_map = get_product_options(data)
            product_label = st.selectbox("Product", options=list(product_map.keys()))
            qty = st.number_input("Quantity", min_value=0.0, step=0.5, value=1.0)
            submitted = st.form_submit_button("Add to Cart")
        if submitted:
            pid = product_map[product_label]
            prod = next(p for p in data["products"] if p["id"] == pid)
            if qty <= 0:
                st.error("Quantity must be greater than zero")
            elif qty > prod["stock"]:
                st.error(f"Not enough stock. Available: {prod['stock']}")
            else:
                st.session_state.cart.append({
                    "product_id": pid,
                    "product_name": prod["name"],
                    "unit": prod["unit"],
                    "price_per_unit": prod["price"],
                    "quantity": qty,
                    "total": qty * prod["price"],
                    "client_id": client_map[client_label]
                })
        # Show cart
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.table(cart_df[["product_name", "quantity", "unit", "price_per_unit", "total"]])
            total_amount = sum(item["total"] for item in st.session_state.cart)
            st.write(f"Total Amount: {format_currency(total_amount)}")
            if st.button("Save Sale"):
                # Persist sale
                items = [{k: v for k, v in item.items() if k in ["product_id", "quantity", "price_per_unit", "total"]} for item in st.session_state.cart]
                client_id = st.session_state.cart[0]["client_id"]
                sale = {
                    "id": len(data["sales"]) + 1,
                    "client_id": client_id,
                    "items": items,
                    "total_amount": total_amount,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                # Update stock
                for item in st.session_state.cart:
                    prod = next(p for p in data["products"] if p["id"] == item["product_id"])
                    prod["stock"] -= item["quantity"]
                data["sales"].append(sale)
                save(data)
                st.success("Sale saved successfully!")
                st.session_state.cart = []
        else:
            st.info("Cart is empty. Add items above.")

    # Date range filter
    st.subheader("Filter Sales")
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input("Start date", datetime.now().replace(day=1))
    with date_col2:
        end_date = st.date_input("End date", datetime.now())

    # Filter sales by date
    data = load()
    filtered_sales = [s for s in data.get("sales", [])
                      if start_date <= datetime.strptime(s["date"].split()[0], "%Y-%m-%d").date() <= end_date]

    # Sales summary
    st.metric("Total Sales in Period", format_currency(sum(s.get("total_amount", 0) for s in filtered_sales)))

    # Sales table
    if filtered_sales:
        sales_rows = []
        for sale in filtered_sales:
            sales_rows.append({
                "Date": sale["date"],
                "Client": get_client_name(sale["client_id"], data),
                "Items": ", ".join([f"{get_product_name(i['product_id'], data)} x{i['quantity']}" for i in sale.get("items", [])]),
                "Total": sale.get("total_amount", 0)
            })
        st.dataframe(pd.DataFrame(sales_rows), use_container_width=True)
    else:
        st.info("No sales found in the selected date range.")

# Clients Page
elif page == "Clients":
    st.title("👥 Clients")
    data = load()
    # Add new client form
    with st.expander("➕ Add New Client"):
        with st.form("add_client"):
            name = st.text_input("Name")
            phone = st.text_input("Phone")
            if st.form_submit_button("Add Client"):
                new_client = {
                    "id": len(data["clients"]) + 1,
                    "name": name,
                    "phone": phone,
                    "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                data["clients"].append(new_client)
                save(data)
                st.success(f"Client '{name}' added successfully!")
    # Clients list
    st.subheader("All Clients")
    data = load()
    if data.get("clients"):
        clients_data = []
        for client in data["clients"]:
            client_sales = [s for s in data.get("sales", []) if s["client_id"] == client["id"]]
            total_spent = sum(s.get("total_amount", 0) for s in client_sales)
            clients_data.append({
                "ID": client["id"],
                "Name": client["name"],
                "Phone": client["phone"],
                "Total Spent": format_currency(total_spent),
                "Purchases": len(client_sales)
            })
        st.dataframe(pd.DataFrame(clients_data), use_container_width=True)
    else:
        st.info("No clients found. Add your first client using the form above.")

# Suppliers Page
elif page == "Suppliers":
    st.title("🏭 Suppliers & Deliveries")
    data = load()
    # Add new supplier form
    with st.expander("➕ Add New Supplier"):
        with st.form("add_supplier"):
            name = st.text_input("Name")
            phone = st.text_input("Phone")
            if st.form_submit_button("Add Supplier"):
                new_supplier = {
                    "id": len(data["suppliers"]) + 1,
                    "name": name,
                    "phone": phone,
                    "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                data["suppliers"].append(new_supplier)
                save(data)
                st.success(f"Supplier '{name}' added successfully!")
    # Record delivery
    with st.expander("🚚 Record Delivery"):
        if not data.get("suppliers") or not data.get("products"):
            st.info("Add suppliers and products first.")
        else:
            with st.form("record_delivery"):
                sup_map = {f"{s['name']} (ID {s['id']})": s['id'] for s in data['suppliers']}
                supplier_label = st.selectbox("Supplier", list(sup_map.keys()))
                prod_map = get_product_options(data)
                product_label = st.selectbox("Product", list(prod_map.keys()))
                qty = st.number_input("Quantity", min_value=0.0, step=0.5, value=1.0)
                price = st.number_input("Price per unit (Ksh)", min_value=0.0, step=1.0)
                if st.form_submit_button("Save Delivery"):
                    pid = prod_map[product_label]
                    sid = sup_map[supplier_label]
                    total_cost = qty * price
                    delivery = {
                        "id": len(data["deliveries"]) + 1,
                        "supplier_id": sid,
                        "product_id": pid,
                        "quantity": qty,
                        "price_per_unit": price,
                        "total_cost": total_cost,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    # Update stock
                    prod = next(p for p in data["products"] if p["id"] == pid)
                    prod["stock"] += qty
                    data["deliveries"].append(delivery)
                    save(data)
                    st.success("Delivery recorded and stock updated.")
    # Suppliers list
    st.subheader("All Suppliers")
    data = load()
    if data.get("suppliers"):
        suppliers_data = []
        for supplier in data["suppliers"]:
            supplier_deliveries = [d for d in data.get("deliveries", []) if d["supplier_id"] == supplier["id"]]
            total_delivered = sum(d.get("quantity", 0) for d in supplier_deliveries)
            total_cost = sum(d.get("total_cost", 0) for d in supplier_deliveries)
            suppliers_data.append({
                "ID": supplier["id"],
                "Name": supplier["name"],
                "Phone": supplier["phone"],
                "Total Delivered": f"{total_delivered:.2f}",
                "Total Cost": format_currency(total_cost)
            })
        st.dataframe(pd.DataFrame(suppliers_data), use_container_width=True)
    else:
        st.info("No suppliers found. Add your first supplier using the form above.")

# Products Page
elif page == "Products":
    st.title("🧺 Products & Inventory")
    data = load()
    if not data.get("products"):
        st.info("No products found in inventory.")
        if st.button("Seed sample products"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            data["products"] = [
                {"id": 1, "name": "Fresh Milk", "price": 60.0, "unit": "liter", "stock": 50.0, "date_added": now},
                {"id": 2, "name": "Mala", "price": 50.0, "unit": "packet", "stock": 30.0, "date_added": now},
                {"id": 3, "name": "Yogurt", "price": 80.0, "unit": "bottle", "stock": 20.0, "date_added": now},
            ]
            save(data)
            st.success("Sample products added.")
            st.rerun()
    with st.expander("➕ Add New Product"):
        with st.form("add_product"):
            name = st.text_input("Product Name")
            price = st.number_input("Price per unit (Ksh)", min_value=0.0, step=1.0)
            unit = st.text_input("Unit (e.g., liter, packet, bottle)")
            stock = st.number_input("Initial stock", min_value=0.0, step=0.5)
            if st.form_submit_button("Add Product"):
                next_id = max([p.get("id", 0) for p in data.get("products", [])], default=0) + 1
                new_product = {
                    "id": next_id,
                    "name": name,
                    "price": price,
                    "unit": unit,
                    "stock": stock,
                    "date_added": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                data.setdefault("products", []).append(new_product)
                save(data)
                st.success(f"Product '{name}' added successfully!")
                st.rerun()
    st.subheader("Inventory")
    data = load()
    if data.get("products"):
        inv_rows = []
        for p in data["products"]:
            inv_rows.append({
                "ID": p["id"],
                "Name": p["name"],
                "Price": format_currency(p["price"]),
                "Stock": p["stock"],
                "Unit": p["unit"]
            })
        st.dataframe(pd.DataFrame(inv_rows), use_container_width=True)
    else:
        st.info("No products found. Add a product above.")

# Add some styling
st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)
