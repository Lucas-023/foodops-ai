from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import queries


class GetSalesInput(BaseModel):
    start_date: date = Field(description="First day of the period (inclusive).")
    end_date: date = Field(description="Last day of the period (inclusive).")
    metric: Literal["summary", "top_products", "daily"] = "summary"
    limit: int = Field(default=3, ge=1, le=50, description="Used by top_products.")


def get_sales(session: Session, params: GetSalesInput) -> dict:
    start = datetime.combine(params.start_date, time.min)
    end = datetime.combine(params.end_date + timedelta(days=1), time.min)

    if params.metric == "top_products":
        data = queries.top_products(session, start, end, params.limit)
    elif params.metric == "daily":
        data = queries.daily_sales(session, start, end)
    else:
        data = queries.total_revenue(session, start, end)

    return {"metric": params.metric, "period": [str(params.start_date), str(params.end_date)], "data": data}
