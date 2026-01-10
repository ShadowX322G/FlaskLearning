from app import app, MyTask, db, User
import sqlite3
import os

def test_health_endpoint():
    # Create a test client for the Flask app
    client = app.test_client()
    
    # Send GET request to /health endpoint
    res = client.get("/health")
    
    # Check that the response is 200 OK
    assert res.status_code == 200
    
    # Verify the JSON response contains status "ok"
    assert res.json["status"] == "ok"
    
def login_test_user(client):
    # Add a test user to the database
    with app.app_context():
        user = User(username="testuser", password="testpass")
        db.session.add(user)
        db.session.commit()
    
    # Log in the test user via POST request
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })

def test_create_and_delete_task():
    # Create a test client for the Flask app
    client = app.test_client()

    with app.app_context():
        # Log in the test user
        login_test_user(client)

        # Create a new task via POST request
        response = client.post('/', data={
            'form_type':'task',
            'content':'Test Task'}, follow_redirects=True)
        
        # Verify the task creation response is OK
        assert response.status_code == 200

        # Check that the task was actually added to the database
        task = MyTask.query.first()
        assert task is not None
        assert task.content == 'Test Task'

        # Delete the created task via POST request
        response = client.post('/delete/task/', data={
            'id': task.id}, follow_redirects=True)
        
        # Verify deletion response is OK
        assert response.status_code == 200
        
        # Ensure the task no longer exists in the database
        assert MyTask.query.count() == 0
