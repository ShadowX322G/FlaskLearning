import os
import pytest
from app import app, db

@pytest.fixture(scope="session", autouse=True)
def test_app():
    # Set environment variables to use test databases instead of production
    os.environ["BASE_DATABASE_URI"] = "sqlite:///test_base.db"
    os.environ["TASKS_DATABASE_URI"] = "sqlite:///test_tasks.db"
    os.environ["CHARTS_DATABASE_URI"] = "sqlite:///test_charts.db"

    # Create all tables in the test database context
    with app.app_context():
        db.create_all()

    # Yield control to the tests
    yield

    # Verify environment variables were changed for testing
    assert os.getenv("TASKS_DATABASE_URI") != "sqlite:///tasks.db"
    assert os.getenv("CHARTS_DATABASE_URI") != "sqlite:///charts.db"

    # Cleanup: remove test database files after tests finish
    for db_file in ("test_base.db", "test_tasks.db", "test_charts.db"):
        if os.path.exists(db_file):
            os.remove(db_file)
