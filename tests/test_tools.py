from datetime import date

from app.tools.inventory import GetInventoryInput, get_inventory
from app.tools.menu import SearchMenuInput, search_menu
from app.tools.promotion import CreatePromotionInput, create_promotion
from app.tools.registry import TOOLS
from app.tools.sales import GetSalesInput, get_sales
from data.seed import LOW_STOCK, OVERSTOCK
from eval.run_eval import load_dataset


def test_sales_summary(session):
    result = get_sales(session, GetSalesInput(start_date=date(2026, 9, 1), end_date=date(2026, 9, 30)))
    assert result["data"]["orders"] > 0
    assert result["data"]["revenue"] > 0


def test_top_products_respects_limit(session):
    params = GetSalesInput(start_date=date(2026, 9, 1), end_date=date(2026, 9, 30), metric="top_products", limit=3)
    data = get_sales(session, params)["data"]
    assert len(data) == 3
    assert data[0]["units"] >= data[1]["units"] >= data[2]["units"]


def test_low_stock_matches_seed(session):
    data = get_inventory(session, GetInventoryInput(low_stock_only=True))["data"]
    assert {row["product"] for row in data} == LOW_STOCK


def test_search_menu_by_category(session):
    data = search_menu(session, SearchMenuInput(category="pizzas"))["data"]
    assert {row["product"] for row in data} == {"Margherita Pizza", "Pepperoni Pizza", "Four Cheese Pizza"}


def test_promotion_excludes_low_stock(session):
    result = create_promotion(session, CreatePromotionInput(reference_date=date(2026, 10, 1)))
    names = {c["product"] for c in result["candidates"]}
    assert result["status"] == "proposal"
    assert names.isdisjoint(LOW_STOCK)
    assert all(c["stock_coverage"] >= 2 for c in result["candidates"])
    assert names & OVERSTOCK


def test_registry_schemas():
    for tool in TOOLS.values():
        assert tool.json_schema()["input_schema"]["type"] == "object"


def test_dataset_loads():
    cases = load_dataset()
    assert all({"id", "question", "expected_tools"} <= set(c) for c in cases)
