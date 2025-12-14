from app import app
import sqlite3
import os
def test_health_endpoint():
    client = app.test_client()
    res = client.get("/health")
    assert res.status_code ==200
    assert res.json["status"] == "ok"

def test_database_access():
    db_path = os.getenv("DATABASE_PATH", "tasks.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    conn.close()

def test_create_and_delete_task():
    client = app.test_client()

    # Create task
    response = client.post("/add", data={
        "title": "Test Task",
        "description": "CI test"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Test Task" in response.data

    # Delete task
    response = client.post("/delete/1", follow_redirects=True)
    assert response.status_code == 200