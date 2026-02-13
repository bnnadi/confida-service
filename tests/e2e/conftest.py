"""
E2E test configuration.

Overrides client to use test db_session so the app can see fixture data.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database_service import get_db


@pytest.fixture
def client(db_session):
    """E2E test client with get_db overridden to use test db_session.

    Ensures the app sees fixture data (sample_user, etc.) in the same
    transaction during HTTP requests.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
