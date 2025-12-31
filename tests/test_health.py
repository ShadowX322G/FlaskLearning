from app import app, MyTask, db, User
import sqlite3
import os
def test_health_endpoint():
    client = app.test_client()
    res = client.get("/health")
    assert res.status_code ==200
    assert res.json["status"] == "ok"
    
def login_test_user(client):
    with app.app_context():
        user = User(username="testuser", password="testpass")
        db.session.add(user)
        db.session.commit()
    
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })

def test_create_and_delete_task():
    client = app.test_client()

    with app.app_context():
        login_test_user(client)

        # Create a new task
        response = client.post('/', data={
            'form_type':'task',
            'content':'Test Task'}, follow_redirects=True)
        
        assert response.status_code == 200

        # Verify the task was created
        task = MyTask.query.first()
        assert task is not None
        assert task.content == 'Test Task'

        #Delete the task
        response = client.post('/delete/task/', data={
            'id': task.id}, follow_redirects=True)
        
        assert response.status_code == 200
        assert MyTask.query.count() == 0