# test_main.py
from fastapi.testclient import TestClient
from main import app # Assuming your FastAPI app instance is named 'app' in 'main.py'

client = TestClient(app)

def test_read_root():
    """
    Test if the main page loads correctly and shows the main form.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "URL Shortener" in response.text
    assert '<form action="/shorten" method="post">' in response.text

# Note: Testing endpoints that rely on a live database (like POST /shorten)
# requires a more advanced setup (e.g., a separate test database).
# This is a great starting point for UI and basic endpoint testing.
