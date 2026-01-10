from app import app

def test_app_starts():
    # Create a test client for the Flask app
    client = app.test_client()
    
    # Send a GET request to the root endpoint
    response = client.get('/')
    
    # Assert that the response is either 200 OK or a 302 redirect
    assert response.status_code in (200, 302)
