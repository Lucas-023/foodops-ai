"""Single place where tools are registered for the agent."""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.inventory import GetInventoryInput, get_inventory
from app.tools.menu import SearchMenuInput, search_menu
from app.tools.promotion import CreatePromotionInput, create_promotion
from app.tools.sales import GetSalesInput, get_sales


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable[[Session, BaseModel], dict]

    def json_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool("get_sales", "Revenue, order count, best sellers and daily sales for a period.", GetSalesInput, get_sales),
        Tool("get_inventory", "Current stock levels and low-stock items.", GetInventoryInput, get_inventory),
        Tool("search_menu", "Search products by name, description or category.", SearchMenuInput, search_menu),
        Tool(
            "create_promotion",
            "Propose promotions for overstocked, slow-moving products. Does not change any data.",
            CreatePromotionInput,
            create_promotion,
        ),
    ]
}
