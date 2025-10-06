import os
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
try:
    from dotenv import load_dotenv
    load_dotenv()  # load variables from .env if present
except Exception:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///milkbar.db")

# Ensure Postgres uses SSL when not specified (e.g., Supabase)
if DATABASE_URL.startswith("postgresql") and "sslmode=" not in DATABASE_URL:
    sep = "?" if "?" not in DATABASE_URL else "&"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    price = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    stock = Column(Float, nullable=False, default=0.0)
    date_added = Column(DateTime, default=func.now())


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    date_added = Column(DateTime, default=func.now())


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    date_added = Column(DateTime, default=func.now())


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    date = Column(DateTime, default=func.now())

    client = relationship("Client")
    items = relationship("SaleItem", cascade="all, delete-orphan", back_populates="sale")


class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")


class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    date = Column(DateTime, default=func.now())

    supplier = relationship("Supplier")
    product = relationship("Product")


def init_db() -> None:
    """Create tables if they do not exist. Call this once at startup."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Defer raising to caller to surface a helpful message in the UI/CLI
        raise


def get_session() -> Session:
    return SessionLocal()


# Query helpers

def list_products(db: Session) -> List[Product]:
    return db.query(Product).order_by(Product.id).all()


def list_clients(db: Session) -> List[Client]:
    return db.query(Client).order_by(Client.id).all()


def list_suppliers(db: Session) -> List[Supplier]:
    return db.query(Supplier).order_by(Supplier.id).all()


def list_sales(db: Session) -> List[Sale]:
    return db.query(Sale).order_by(Sale.date.desc()).all()


def list_deliveries(db: Session) -> List[Delivery]:
    return db.query(Delivery).order_by(Delivery.date.desc()).all()


# Create helpers

def create_product(db: Session, name: str, price: float, unit: str, stock: float = 0.0) -> Product:
    p = Product(name=name, price=price, unit=unit, stock=stock)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def create_client(db: Session, name: str, phone: Optional[str] = None) -> Client:
    c = Client(name=name, phone=phone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def create_supplier(db: Session, name: str, phone: Optional[str] = None) -> Supplier:
    s = Supplier(name=name, phone=phone)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def delete_supplier(db: Session, supplier_id: int) -> None:
    """Delete supplier only if no deliveries reference it."""
    has_deliveries = db.query(Delivery).filter(Delivery.supplier_id == supplier_id).first() is not None
    if has_deliveries:
        raise ValueError("Cannot delete supplier with existing deliveries. Delete deliveries first.")
    s = db.query(Supplier).filter(Supplier.id == supplier_id).one()
    db.delete(s)
    db.commit()


def delete_delivery(db: Session, delivery_id: int) -> None:
    """Delete a delivery and reduce product stock accordingly."""
    d = db.query(Delivery).filter(Delivery.id == delivery_id).one()
    prod = db.query(Product).filter(Product.id == d.product_id).one()
    # decrease stock added by this delivery
    new_stock = (prod.stock or 0) - d.quantity
    if new_stock < 0:
        new_stock = 0
    prod.stock = new_stock
    db.delete(d)
    db.commit()


def delete_sale_item(db: Session, sale_item_id: int) -> None:
    """Delete a sale item, restore product stock, and update sale total or delete sale if empty."""
    it = db.query(SaleItem).filter(SaleItem.id == sale_item_id).one()
    sale = db.query(Sale).filter(Sale.id == it.sale_id).one()
    prod = db.query(Product).filter(Product.id == it.product_id).one()
    # restore stock reduced by this sale item
    prod.stock = (prod.stock or 0) + it.quantity
    # adjust sale total
    sale.total_amount = float(sale.total_amount or 0) - float(it.total or (it.quantity * it.price_per_unit))
    if sale.total_amount < 0:
        sale.total_amount = 0.0
    db.delete(it)
    db.flush()
    # if sale has no more items, delete sale
    remaining = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).first()
    if remaining is None:
        db.delete(sale)
    db.commit()


def delete_client(db: Session, client_id: int) -> None:
    """Delete client only if no sales reference it."""
    has_sales = db.query(Sale).filter(Sale.client_id == client_id).first() is not None
    if has_sales:
        raise ValueError("Cannot delete client with existing sales. Delete sales for this client first.")
    c = db.query(Client).filter(Client.id == client_id).one()
    db.delete(c)
    db.commit()


def delete_product(db: Session, product_id: int) -> None:
    """Delete product only if not referenced by deliveries or sale items."""
    has_deliveries = db.query(Delivery).filter(Delivery.product_id == product_id).first() is not None
    has_sale_items = db.query(SaleItem).filter(SaleItem.product_id == product_id).first() is not None
    if has_deliveries or has_sale_items:
        raise ValueError("Cannot delete product that has deliveries or sales. Remove related records first.")
    p = db.query(Product).filter(Product.id == product_id).one()
    db.delete(p)
    db.commit()


def delete_sale(db: Session, sale_id: int) -> None:
    """Delete a sale and its items, restoring product stock quantities."""
    s = db.query(Sale).filter(Sale.id == sale_id).one()
    # restore stock
    for it in s.items:
        prod = db.query(Product).filter(Product.id == it.product_id).one()
        prod.stock = (prod.stock or 0) + it.quantity
    db.delete(s)
    db.commit()


def record_delivery(db: Session, supplier_id: int, product_id: int, quantity: float, price_per_unit: float) -> Delivery:
    total_cost = quantity * price_per_unit
    d = Delivery(
        supplier_id=supplier_id,
        product_id=product_id,
        quantity=quantity,
        price_per_unit=price_per_unit,
        total_cost=total_cost,
    )
    # update stock
    prod = db.query(Product).filter(Product.id == product_id).one()
    prod.stock = (prod.stock or 0) + quantity
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def record_sale(db: Session, client_id: int, items: List[Dict]) -> Sale:
    """
    items: list of {product_id, quantity, price_per_unit}
    """
    total = 0.0
    sale_items: List[SaleItem] = []
    for it in items:
        pid = int(it["product_id"])
        qty = float(it["quantity"])
        price = float(it.get("price_per_unit"))
        line_total = qty * price
        total += line_total
        sale_items.append(SaleItem(product_id=pid, quantity=qty, price_per_unit=price, total=line_total))
    s = Sale(client_id=client_id, total_amount=total)
    s.items = sale_items

    # update stock
    for it in sale_items:
        prod = db.query(Product).filter(Product.id == it.product_id).one()
        if prod.stock is None:
            prod.stock = 0
        if prod.stock < it.quantity:
            raise ValueError(f"Insufficient stock for {prod.name}. Available: {prod.stock}, requested: {it.quantity}")
        prod.stock -= it.quantity

    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# Utilities to snapshot DB into dicts suitable for CSV export

def snapshot(db: Session) -> Dict:
    prods = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "unit": p.unit,
            "stock": p.stock,
            "date_added": p.date_added.strftime("%Y-%m-%d %H:%M:%S") if p.date_added else None,
        }
        for p in list_products(db)
    ]
    clients = [
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "date_added": c.date_added.strftime("%Y-%m-%d %H:%M:%S") if c.date_added else None,
        }
        for c in list_clients(db)
    ]
    suppliers = [
        {
            "id": s.id,
            "name": s.name,
            "phone": s.phone,
            "date_added": s.date_added.strftime("%Y-%m-%d %H:%M:%S") if s.date_added else None,
        }
        for s in list_suppliers(db)
    ]
    deliveries = [
        {
            "id": d.id,
            "supplier_id": d.supplier_id,
            "product_id": d.product_id,
            "quantity": d.quantity,
            "price_per_unit": d.price_per_unit,
            "total_cost": d.total_cost,
            "date": d.date.strftime("%Y-%m-%d %H:%M:%S") if d.date else None,
        }
        for d in list_deliveries(db)
    ]
    sales = []
    for s in list_sales(db):
        sales.append(
            {
                "id": s.id,
                "client_id": s.client_id,
                "items": [
                    {
                        "id": it.id,
                        "product_id": it.product_id,
                        "quantity": it.quantity,
                        "price_per_unit": it.price_per_unit,
                        "total": it.total,
                    }
                    for it in s.items
                ],
                "total_amount": s.total_amount,
                "date": s.date.strftime("%Y-%m-%d %H:%M:%S") if s.date else None,
            }
        )
    return {
        "products": prods,
        "clients": clients,
        "suppliers": suppliers,
        "deliveries": deliveries,
        "sales": sales,
    }


# Admin utilities
def reset_all(db: Session) -> None:
    """Dangerous: clear all tables and restart identities.
    Uses TRUNCATE on Postgres; falls back to manual deletes on SQLite.
    """
    try:
        # Works on Postgres
        db.execute(
            "TRUNCATE TABLE sale_items, sales, deliveries, products, clients, suppliers RESTART IDENTITY CASCADE;"
        )
        db.commit()
        return
    except Exception:
        # Fallback for SQLite or other engines: manual delete respecting FKs
        db.execute("DELETE FROM sale_items;")
        db.execute("DELETE FROM sales;")
        db.execute("DELETE FROM deliveries;")
        db.execute("DELETE FROM products;")
        db.execute("DELETE FROM clients;")
        db.execute("DELETE FROM suppliers;")
        try:
            # Reset SQLite AUTOINCREMENT where supported
            db.execute("DELETE FROM sqlite_sequence WHERE name IN ('sale_items','sales','deliveries','products','clients','suppliers');")
        except Exception:
            pass
        db.commit()


def update_product(db: Session, product_id: int, name: Optional[str] = None, price: Optional[float] = None, unit: Optional[str] = None, stock: Optional[float] = None) -> Product:
    p = db.query(Product).filter(Product.id == product_id).one()
    if name is not None:
        p.name = name
    if price is not None:
        p.price = price
    if unit is not None:
        p.unit = unit
    if stock is not None:
        p.stock = stock
    db.commit()
    db.refresh(p)
    return p


def update_client(db: Session, client_id: int, name: Optional[str] = None, phone: Optional[str] = None) -> Client:
    c = db.query(Client).filter(Client.id == client_id).one()
    if name is not None:
        c.name = name
    if phone is not None:
        c.phone = phone
    db.commit()
    db.refresh(c)
    return c


def update_supplier(db: Session, supplier_id: int, name: Optional[str] = None, phone: Optional[str] = None) -> Supplier:
    s = db.query(Supplier).filter(Supplier.id == supplier_id).one()
    if name is not None:
        s.name = name
    if phone is not None:
        s.phone = phone
    db.commit()
    db.refresh(s)
    return s
