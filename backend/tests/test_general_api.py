import os
import shutil

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_and_teardown_test_dir():
    test_dir = "test_local_storage"
    db_file = "database.db"

    print("Current working directory:", os.getcwd())

    # Create the test directory
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    yield

    # Teardown: Delete the database file and the test directory
    try:
        if os.path.exists(db_file):
            os.remove(db_file)
    except Exception as e:
        print(f"Error deleting database file: {e}")

    try:
        shutil.rmtree(test_dir)
    except Exception as e:
        print(f"Error deleting test directory: {e}")


@pytest.fixture
def app():
    from ..src.main import app as _app

    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_api_root(client):
    """Test the root endpoint of the API. Ensure the API is running."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, hello!"}
