from app import app

def test_app_starts():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code in (200, 302)