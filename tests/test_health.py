from app import app, MyTask, db
import sqlite3
import os
def test_health_endpoint():
    client = app.test_client()
    res = client.get("/health")
    assert res.status_code ==200
    assert res.json["status"] == "ok"

def test_create_and_delete_task():
    client = app.test_client()

    with app.app_context():
        # CREATE
        response = client.post("/", data={"content": "Test Task"}, follow_redirects=True)
        assert response.status_code == 200

        # READ from DB
        task = MyTask.query.first()
        assert task is not None
        assert task.content == "Test Task"

        # DELETE
        client.get(f"/delete/{task.id}", follow_redirects=True)
        assert MyTask.query.count() == 0  