from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import queries


class SearchMenuInput(BaseModel):
    query: str | None = Field(default=None, description="Text matched against name and description.")
    category: str | None = Field(default=None, description="Exact category, e.g. 'burgers'.")


def search_menu(session: Session, params: SearchMenuInput) -> dict:
    return {"data": queries.search_products(session, params.query, params.category)}
