from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base
from data.seed import seed

SEED_END = datetime(2026, 10, 1)


@pytest.fixture(scope="session")
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        seed(s, days=30, end=SEED_END)
        yield s
