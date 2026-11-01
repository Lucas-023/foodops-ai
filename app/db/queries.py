"""Read-only queries used by the agent tools.

Every function returns plain dicts so results can be serialized and passed to the LLM.
"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Inventory, Order, OrderItem, Product

_line_total = OrderItem.quantity * OrderItem.unit_price


def total_revenue(session: Session, start: datetime, end: datetime) -> dict:
    stmt = (
        select(func.coalesce(func.sum(_line_total), 0), func.count(func.distinct(Order.id)))
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.created_at >= start, Order.created_at < end)
    )
    revenue, n_orders = session.execute(stmt).one()
    revenue = float(revenue)
    return {
        "revenue": round(revenue, 2),
        "orders": n_orders,
        "average_order_value": round(revenue / n_orders, 2) if n_orders else 0.0,
    }


def top_products(session: Session, start: datetime, end: datetime, limit: int = 3) -> list[dict]:
    units = func.sum(OrderItem.quantity).label("units")
    stmt = (
        select(Product.name, units, func.sum(_line_total).label("revenue"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.created_at >= start, Order.created_at < end)
        .group_by(Product.name)
        .order_by(units.desc())
        .limit(limit)
    )
    return [
        {"product": name, "units": int(u), "revenue": round(float(r), 2)}
        for name, u, r in session.execute(stmt)
    ]


def daily_sales(session: Session, start: datetime, end: datetime) -> list[dict]:
    day = func.date(Order.created_at).label("day")
    stmt = (
        select(day, func.sum(_line_total))
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.created_at >= start, Order.created_at < end)
        .group_by(day)
        .order_by(day)
    )
    return [{"day": str(d), "revenue": round(float(r), 2)} for d, r in session.execute(stmt)]


def inventory_status(session: Session, low_stock_only: bool = False) -> list[dict]:
    stmt = select(Product.name, Inventory.quantity, Inventory.min_quantity, Inventory.unit).join(
        Inventory, Inventory.product_id == Product.id
    )
    if low_stock_only:
        stmt = stmt.where(Inventory.quantity <= Inventory.min_quantity)
    stmt = stmt.order_by(Inventory.quantity - Inventory.min_quantity)
    return [
        {
            "product": name,
            "quantity": qty,
            "min_quantity": min_qty,
            "unit": unit,
            "low_stock": qty <= min_qty,
        }
        for name, qty, min_qty, unit in session.execute(stmt)
    ]


def search_products(
    session: Session, query: str | None = None, category: str | None = None
) -> list[dict]:
    stmt = select(Product)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
    if category:
        stmt = stmt.where(Product.category.ilike(category))
    return [
        {
            "product": p.name,
            "category": p.category,
            "description": p.description,
            "price": float(p.price),
            "available": p.is_available,
        }
        for p in session.scalars(stmt.order_by(Product.name))
    ]
