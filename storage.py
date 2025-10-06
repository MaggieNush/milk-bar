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


# Create tables
Base.metadata.create_all(bind=engine)


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
