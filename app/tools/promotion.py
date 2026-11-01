"""Promotion proposals. Recommendations only: this never writes to the database."""

from datetime import date, datetime, time, timedelta

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import queries


class CreatePromotionInput(BaseModel):
    reference_date: date = Field(description="Sales are analysed over the 7 days before this date.")
    max_items: int = Field(default=3, ge=1, le=10)


def create_promotion(session: Session, params: CreatePromotionInput) -> dict:
    end = datetime.combine(params.reference_date, time.min)
    start = end - timedelta(days=7)

    units_sold = {
        row["product"]: row["units"] for row in queries.top_products(session, start, end, limit=1000)
    }
    stock = queries.inventory_status(session)

    # Overstocked + slow-moving items are the natural promotion candidates.
    candidates = []
    for item in stock:
        if item["min_quantity"] == 0:
            continue
        coverage = item["quantity"] / item["min_quantity"]
        sold = units_sold.get(item["product"], 0)
        if coverage >= 2:
            candidates.append({**item, "units_sold_last_7d": sold, "stock_coverage": round(coverage, 2)})

    candidates.sort(key=lambda c: (c["units_sold_last_7d"], -c["stock_coverage"]))
    return {
        "status": "proposal",
        "analysis_window": [str(start.date()), str(end.date())],
        "candidates": candidates[: params.max_items],
    }
