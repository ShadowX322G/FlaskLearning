import os
import pytest
from app import app, db

@pytest.fixture(scope="session", autouse=True)
def test_app():
    os.environ["BASE_DATABASE_URI"] = "sqlite:///test_base.db"
    os.environ["TASKS_DATABASE_URI"] = "sqlite:///test_tasks.db"
    os.environ["CHARTS_DATABASE_URI"] = "sqlite:///test_charts.db"

    with app.app_context():
        db.create_all()

    yield

    assert os.getenv("TASKS_DATABASE_URI") != "sqlite:///tasks.db"
    assert os.getenv("CHARTS_DATABASE_URI") != "sqlite:///charts.db"


    # cleanup
    for db_file in ("test_base.db", "test_tasks.db", "test_charts.db"):
        if os.path.exists(db_file):
            os.remove(db_file)
