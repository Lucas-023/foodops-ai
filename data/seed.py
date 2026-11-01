"""Generate a deterministic synthetic restaurant dataset.

Usage:
    python -m data.seed --days 90 --reset
"""

import argparse
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Base, Inventory, Order, OrderItem, Product

# name, category, description, price, popularity weight
PRODUCTS = [
    ("Classic Burger", "burgers", "Beef patty, cheddar, lettuce, tomato, house sauce.", "32.90", 10),
    ("Bacon Burger", "burgers", "Beef patty, crispy bacon, cheddar, caramelized onion.", "38.90", 8),
    ("Veggie Burger", "burgers", "Chickpea patty, avocado, arugula, vegan mayo.", "34.90", 4),
    ("Chicken Sandwich", "sandwiches", "Grilled chicken breast, mozzarella, pesto.", "29.90", 6),
    ("Club Sandwich", "sandwiches", "Turkey, bacon, egg, lettuce, toasted bread.", "31.90", 3),
    ("Margherita Pizza", "pizzas", "Tomato sauce, mozzarella, fresh basil.", "49.90", 7),
    ("Pepperoni Pizza", "pizzas", "Tomato sauce, mozzarella, pepperoni.", "54.90", 7),
    ("Four Cheese Pizza", "pizzas", "Mozzarella, gorgonzola, parmesan, provolone.", "56.90", 4),
    ("Caesar Salad", "salads", "Romaine, parmesan, croutons, caesar dressing.", "27.90", 4),
    ("Greek Salad", "salads", "Tomato, cucumber, olives, feta, red onion.", "26.90", 2),
    ("French Fries", "sides", "Crispy fries with sea salt.", "14.90", 12),
    ("Onion Rings", "sides", "Beer-battered onion rings.", "17.90", 5),
    ("Sweet Potato Fries", "sides", "Sweet potato fries with paprika.", "18.90", 3),
    ("Cola", "drinks", "350ml can.", "7.90", 11),
    ("Orange Juice", "drinks", "Freshly squeezed, 400ml.", "11.90", 5),
    ("Lemonade", "drinks", "House lemonade with mint, 400ml.", "10.90", 6),
    ("Craft Beer", "drinks", "Local IPA, 500ml.", "19.90", 4),
    ("Brownie", "desserts", "Chocolate brownie with walnuts.", "15.90", 5),
    ("Cheesecake", "desserts", "New York style with berry coulis.", "18.90", 3),
    ("Ice Cream", "desserts", "Two scoops, vanilla or chocolate.", "12.90", 4),
]

# Products deliberately left low on stock so low-stock questions have known answers.
LOW_STOCK = {"Bacon Burger", "Orange Juice", "Cheesecake"}
# Products deliberately overstocked so promotion questions have known answers.
OVERSTOCK = {"Greek Salad", "Sweet Potato Fries", "Club Sandwich"}

CHANNELS = [("dine_in", 5), ("takeaway", 2), ("delivery", 3)]
WEEKDAY_FACTOR = [0.8, 0.8, 0.9, 1.0, 1.3, 1.5, 1.2]  # Mon..Sun
HOURS = [(11, 1), (12, 4), (13, 3), (14, 1), (18, 1), (19, 3), (20, 4), (21, 2), (22, 1)]


def _weighted(rng: random.Random, pairs):
    values, weights = zip(*pairs)
    return rng.choices(values, weights=weights, k=1)[0]


def seed(session: Session, days: int = 90, end: datetime | None = None, rng_seed: int = 42) -> None:
    rng = random.Random(rng_seed)
    end = (end or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)

    products = [
        Product(name=n, category=c, description=d, price=Decimal(p), is_available=True)
        for n, c, d, p, _ in PRODUCTS
    ]
    session.add_all(products)
    session.flush()
    weights = {p.id: w for p, (*_, w) in zip(products, PRODUCTS)}

    for p in products:
        min_qty = 20
        if p.name in LOW_STOCK:
            qty = rng.randint(3, 15)
        elif p.name in OVERSTOCK:
            qty = rng.randint(90, 140)
        else:
            qty = rng.randint(30, 80)
        session.add(Inventory(product_id=p.id, quantity=qty, min_quantity=min_qty, updated_at=end))

    product_pairs = [(p, weights[p.id]) for p in products]
    for offset in range(days):
        day = start + timedelta(days=offset)
        n_orders = int(rng.gauss(60, 8) * WEEKDAY_FACTOR[day.weekday()])
        for _ in range(max(n_orders, 0)):
            created = day.replace(hour=_weighted(rng, HOURS), minute=rng.randint(0, 59))
            order = Order(created_at=created, channel=_weighted(rng, CHANNELS))
            chosen: dict[int, OrderItem] = {}
            for _ in range(rng.randint(1, 4)):
                product = _weighted(rng, product_pairs)
                if product.id in chosen:
                    chosen[product.id].quantity += 1
                else:
                    chosen[product.id] = OrderItem(product_id=product.id, quantity=1, unit_price=product.price)
            order.items = list(chosen.values())
            session.add(order)

    session.commit()


def main() -> None:
    from app.db.session import SessionLocal, engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first.")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        if session.query(Product).first() and not args.reset:
            raise SystemExit("Database already has data. Use --reset to recreate it.")
        seed(session, days=args.days, rng_seed=args.seed)
    print(f"Seeded {args.days} days of data.")


if __name__ == "__main__":
    main()
