import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from milk_bar import load_data, get_client_name, get_supplier_name, get_product_name
from export_utils import export_all_csv

# Configure database URL from Streamlit secrets if available BEFORE importing storage
try:
    # Only set from secrets if DATABASE_URL is not already provided (e.g., by local shell)
    if not os.environ.get("DATABASE_URL") and "postgres" in st.secrets and st.secrets["postgres"].get("uri"):
        uri = st.secrets["postgres"]["uri"]
        # Ensure driver is psycopg2 for SQLAlchemy
        if uri.startswith("postgresql://") and "+psycopg2" not in uri:
            uri = uri.replace("postgresql://", "postgresql+psycopg2://", 1)
        os.environ["DATABASE_URL"] = uri
except Exception:
    pass

from storage import (
    get_session,
    list_products, list_clients, list_suppliers, list_deliveries, list_sales,
    create_product, create_client, create_supplier, record_delivery, record_sale,
    snapshot, init_db, update_product, update_client, update_supplier,
    delete_sale, delete_supplier, delete_product, delete_client, delete_delivery, delete_sale_item,
)

# Set page config
st.set_page_config(
    page_title="Mama's Milk Bar Dashboard",
    page_icon="🥛",
    layout="wide"
)

# Initialize DB (creates tables if missing)
try:
    init_db()
except Exception as e:
    st.error(f"Database initialization failed: {e}")

# Helper functions
def load():
    # Pull a fresh snapshot from DB for display
    with get_session() as db:
        return snapshot(db)

def save_export_from_db():
    # Export CSVs from current DB state
    try:
        with get_session() as db:
            data = snapshot(db)
        export_all_csv(data, out_dir="exports")
    except Exception as e:
        st.warning(f"CSV export failed: {e}")

# Load data
data = load()

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Sales", "Clients", "Suppliers", "Products", "Admin"])

# Helper functions
def format_currency(amount):
    return f"Ksh {amount:,.2f}"

def get_client_options(d):
    return {f"{c['name']} (ID {c['id']})": c['id'] for c in d.get('clients', [])}

def get_product_options(d):
    return {f"{p['name']} - Ksh {p['price']}/{p['unit']} (Stock: {p['stock']})": p['id'] for p in d.get('products', [])}

# Dashboard Page
if page == "Dashboard":
    st.title("Mama's Milk Bar Dashboard")
    
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
    st.title("Sales Overview & Record Sale")

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
                # Persist sale to DB
                client_id = int(st.session_state.cart[0]["client_id"])
                items = [
                    {
                        "product_id": int(item["product_id"]),
                        "quantity": float(item["quantity"]),
                        "price_per_unit": float(item["price_per_unit"]),
                    }
                    for item in st.session_state.cart
                ]
                try:
                    with get_session() as db:
                        record_sale(db, client_id=client_id, items=items)
                    save_export_from_db()
                    st.success("Sale saved successfully!")
                    st.session_state.cart = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save sale: {e}")
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
    st.title("Clients")
    data = load()
    # Add new client form
    with st.expander("➕ Add New Client"):
        with st.form("add_client"):
            name = st.text_input("Name")
            phone = st.text_input("Phone")
            if st.form_submit_button("Add Client"):
                try:
                    with get_session() as db:
                        create_client(db, name=name, phone=phone)
                    save_export_from_db()
                    st.success(f"Client '{name}' added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add client: {e}")
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
    st.title("Suppliers & Deliveries")
    data = load()
    # Add new supplier form
    with st.expander("➕ Add New Supplier"):
        with st.form("add_supplier"):
            name = st.text_input("Name")
            phone = st.text_input("Phone")
            if st.form_submit_button("Add Supplier"):
                try:
                    with get_session() as db:
                        create_supplier(db, name=name, phone=phone)
                    save_export_from_db()
                    st.success(f"Supplier '{name}' added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add supplier: {e}")
    # Record delivery
    with st.expander("Record Delivery"):
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
                    pid = int(prod_map[product_label])
                    sid = int(sup_map[supplier_label])
                    try:
                        with get_session() as db:
                            record_delivery(db, supplier_id=sid, product_id=pid, quantity=float(qty), price_per_unit=float(price))
                        save_export_from_db()
                        st.success("Delivery recorded and stock updated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to record delivery: {e}")
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
    st.title("Products & Inventory")
    data = load()
    if not data.get("products"):
        st.info("No products found in inventory.")
        if st.button("Seed sample products"):
            try:
                with get_session() as db:
                    create_product(db, name="Fresh Milk", price=60.0, unit="liter", stock=50.0)
                    create_product(db, name="Mala", price=50.0, unit="packet", stock=30.0)
                    create_product(db, name="Yogurt", price=80.0, unit="bottle", stock=20.0)
                save_export_from_db()
                st.success("Sample products added.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to seed products: {e}")
    with st.expander("➕ Add New Product"):
        with st.form("add_product"):
            name = st.text_input("Product Name")
            price = st.number_input("Price per unit (Ksh)", min_value=0.0, step=1.0)
            unit = st.text_input("Unit (e.g., liter, packet, bottle)")
            stock = st.number_input("Initial stock", min_value=0.0, step=0.5)
            if st.form_submit_button("Add Product"):
                try:
                    with get_session() as db:
                        create_product(db, name=name, price=float(price), unit=unit, stock=float(stock))
                    save_export_from_db()
                    st.success(f"Product '{name}' added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add product: {e}")
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
        st.dataframe(pd.DataFrame(inv_rows))
    else:
        st.info("No products found. Add your first product using the form above.")

# Admin Page
elif page == "Admin":
    st.title(" Admin")
    st.caption("View data, make quick edits, export CSVs, and reset all data (dangerous).")

    # Counts
    with get_session() as db:
        counts = {
            "Products": len(list_products(db)),
            "Clients": len(list_clients(db)),
            "Suppliers": len(list_suppliers(db)),
            "Deliveries": len(list_deliveries(db)),
            "Sales": len(list_sales(db)),
        }
    cols = st.columns(len(counts))
    for (label, value), col in zip(counts.items(), cols):
        with col:
            st.metric(label, value)

    st.subheader("Browse Tables")
    data = load()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Products", "Clients", "Suppliers", "Deliveries", "Sales"])
    with tab1:
        st.dataframe(pd.DataFrame(data.get("products", [])))
    with tab2:
        st.dataframe(pd.DataFrame(data.get("clients", [])))
    with tab3:
        st.dataframe(pd.DataFrame(data.get("suppliers", [])))
    with tab4:
        st.dataframe(pd.DataFrame(data.get("deliveries", [])))
    with tab5:
        st.write("Sales are nested (items inside each sale). Export CSVs to see line items.")
        st.dataframe(pd.DataFrame(data.get("sales", [])))

    st.subheader("Quick Edits")
    edit_tab1, edit_tab2, edit_tab3 = st.tabs(["Edit Product", "Edit Client", "Edit Supplier"])
    with edit_tab1:
        if data.get("products"):
            prod_map = {f"{p['id']}: {p['name']}": p['id'] for p in data["products"]}
            sel = st.selectbox("Select product", list(prod_map.keys()))
            pid = prod_map[sel]
            name = st.text_input("Name", value=next(p['name'] for p in data['products'] if p['id']==pid))
            price = st.number_input("Price", min_value=0.0, step=1.0, value=float(next(p['price'] for p in data['products'] if p['id']==pid)))
            unit = st.text_input("Unit", value=next(p['unit'] for p in data['products'] if p['id']==pid))
            stock = st.number_input("Stock", min_value=0.0, step=0.5, value=float(next(p['stock'] for p in data['products'] if p['id']==pid)))
            if st.button("Save Product Changes"):
                try:
                    with get_session() as db:
                        update_product(db, pid, name=name, price=price, unit=unit, stock=stock)
                    save_export_from_db()
                    st.success("Product updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update product: {e}")
        else:
            st.info("No products to edit.")
    with edit_tab2:
        if data.get("clients"):
            cli_map = {f"{c['id']}: {c['name']}": c['id'] for c in data["clients"]}
            sel = st.selectbox("Select client", list(cli_map.keys()))
            cid = cli_map[sel]
            name = st.text_input("Name", value=next(c['name'] for c in data['clients'] if c['id']==cid))
            phone = st.text_input("Phone", value=next((c.get('phone') or '') for c in data['clients'] if c['id']==cid))
            if st.button("Save Client Changes"):
                try:
                    with get_session() as db:
                        update_client(db, cid, name=name, phone=phone)
                    save_export_from_db()
                    st.success("Client updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update client: {e}")
        else:
            st.info("No clients to edit.")
    with edit_tab3:
        if data.get("suppliers"):
            sup_map = {f"{s['id']}: {s['name']}": s['id'] for s in data["suppliers"]}
            sel = st.selectbox("Select supplier", list(sup_map.keys()))
            sid = sup_map[sel]
            name = st.text_input("Name", value=next(s['name'] for s in data['suppliers'] if s['id']==sid))
            phone = st.text_input("Phone", value=next((s.get('phone') or '') for s in data['suppliers'] if s['id']==sid))
            if st.button("Save Supplier Changes"):
                try:
                    with get_session() as db:
                        update_supplier(db, sid, name=name, phone=phone)
                    save_export_from_db()
                    st.success("Supplier updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update supplier: {e}")
        else:
            st.info("No suppliers to edit.")

    st.subheader("Export & Delete Records")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Download all CSVs (regenerate)"):
            save_export_from_db()
            st.success("CSV export regenerated in exports/.")
    with col_b:
        st.write("Delete individual records safely (requires confirmation):")
        with st.expander("🧾 Delete Sale"):
            data = load()
            if data.get("sales"):
                sale_map = {f"{s['id']}: Ksh {s['total_amount']} on {s['date']}": s['id'] for s in data['sales']}
                sel = st.selectbox("Select sale", list(sale_map.keys()), key="del_sale_sel")
                confirm = st.checkbox("Confirm delete sale", key="del_sale_confirm")
                if st.button("Delete Sale", key="del_sale_btn", disabled=not confirm):
                    try:
                        with get_session() as db:
                            delete_sale(db, sale_map[sel])
                        save_export_from_db()
                        st.success("Sale deleted and stock restored.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete sale: {e}")
            else:
                st.info("No sales to delete.")
        with st.expander("🏭 Delete Supplier"):
            data = load()
            if data.get("suppliers"):
                sup_map = {f"{s['id']}: {s['name']}": s['id'] for s in data['suppliers']}
                sel = st.selectbox("Select supplier", list(sup_map.keys()), key="del_sup_sel")
                confirm = st.checkbox("Confirm delete supplier", key="del_sup_confirm")
                if st.button("Delete Supplier", key="del_sup_btn", disabled=not confirm):
                    try:
                        with get_session() as db:
                            delete_supplier(db, sup_map[sel])
                        save_export_from_db()
                        st.success("Supplier deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete supplier: {e}")
            else:
                st.info("No suppliers to delete.")
        with st.expander("🧺 Delete Product"):
            data = load()
            if data.get("products"):
                prod_map = {f"{p['id']}: {p['name']}": p['id'] for p in data['products']}
                sel = st.selectbox("Select product", list(prod_map.keys()), key="del_prod_sel")
                confirm = st.checkbox("Confirm delete product", key="del_prod_confirm")
                if st.button("Delete Product", key="del_prod_btn", disabled=not confirm):
                    try:
                        with get_session() as db:
                            delete_product(db, prod_map[sel])
                        save_export_from_db()
                        st.success("Product deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete product: {e}")
            else:
                st.info("No products to delete.")

        with st.expander("👥 Delete Client"):
            data = load()
            if data.get("clients"):
                cli_map = {f"{c['id']}: {c['name']}": c['id'] for c in data['clients']}
                sel = st.selectbox("Select client", list(cli_map.keys()), key="del_cli_sel")
                confirm = st.checkbox("Confirm delete client", key="del_cli_confirm")
                if st.button("Delete Client", key="del_cli_btn", disabled=not confirm):
                    try:
                        with get_session() as db:
                            delete_client(db, cli_map[sel])
                        save_export_from_db()
                        st.success("Client deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete client: {e}")
            else:
                st.info("No clients to delete.")

        with st.expander("🚚 Delete Delivery"):
            data = load()
            if data.get("deliveries"):
                deliv_map = {}
                options = []
                for d in data["deliveries"]:
                    label = f"{d['id']}: {get_product_name(d['product_id'], data)} x{d['quantity']} on {d['date']}"
                    deliv_map[label] = d['id']
                    options.append(label)
                sel = st.selectbox("Select delivery", options, key="del_delivery_sel")
                confirm = st.checkbox("Confirm delete delivery", key="del_delivery_confirm")
                if st.button("Delete Delivery", key="del_delivery_btn", disabled=not confirm):
                    try:
                        with get_session() as db:
                            delete_delivery(db, deliv_map[sel])
                        save_export_from_db()
                        st.success("Delivery deleted and stock reduced accordingly.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete delivery: {e}")
            else:
                st.info("No deliveries to delete.")

        with st.expander("🧾 Delete Sale Item"):
            data = load()
            # Build options from sale items with their IDs
            sale_item_options = []
            sale_item_map = {}
            for s in data.get("sales", []):
                for it in s.get("items", []):
                    label = f"Item {it['id']} (Sale {s['id']}): {get_product_name(it['product_id'], data)} x{it['quantity']} at {it['price_per_unit']} on {s['date']}"
                    sale_item_options.append(label)
                    sale_item_map[label] = it['id']
            if sale_item_options:
                sel = st.selectbox("Select sale item", sale_item_options, key="del_sale_item_sel")
                confirm = st.checkbox("Confirm delete sale item", key="del_sale_item_confirm")
                if st.button("Delete Sale Item", key="del_sale_item_btn", disabled=not confirm):
                    try:
                        with get_session() as db:
                            delete_sale_item(db, sale_item_map[sel])
                        save_export_from_db()
                        st.success("Sale item deleted; sale total and stock adjusted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete sale item: {e}")
            else:
                st.info("No sale items to delete.")


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
