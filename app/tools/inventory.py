from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import queries


class GetInventoryInput(BaseModel):
    low_stock_only: bool = Field(default=False, description="Return only items at or below minimum.")


def get_inventory(session: Session, params: GetInventoryInput) -> dict:
    return {"data": queries.inventory_status(session, params.low_stock_only)}
