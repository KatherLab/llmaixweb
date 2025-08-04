def test_api_root(client):
    """Test the root endpoint of the API. Ensure the API is running."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, hello!"}
