"""
Tests for authentication functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.services.auth_service import AuthService


def test_user_registration(client: TestClient, db_session: Session):
    """Test user registration endpoint."""
    user_data = {
        "email": "register-test@example.com",
        "password": "TestPassword123",
        "name": "Test User"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert "id" in data
    assert "password" not in data  # Password should not be returned
    assert "password_hash" not in data


def test_user_registration_duplicate_email(client: TestClient, db_session: Session):
    """Test user registration with duplicate email."""
    user_data = {
        "email": "duplicate-test@example.com",
        "password": "TestPassword123",
        "name": "Test User"
    }
    
    # Register first user
    response1 = client.post("/api/v1/auth/register", json=user_data)
    assert response1.status_code == 201
    
    # Try to register with same email
    response2 = client.post("/api/v1/auth/register", json=user_data)
    assert response2.status_code == 400
    assert "Email already registered" in response2.json()["detail"]


def test_user_registration_invalid_password(client: TestClient, db_session: Session):
    """Test user registration with invalid password."""
    user_data = {
        "email": "invalid-pass-test@example.com",
        "password": "weak",  # Too short
        "name": "Test User"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 422  # Validation error


def test_user_login_success(client: TestClient, db_session: Session):
    """Test successful user login."""
    # First register a user
    user_data = {
        "email": "login-test@example.com",
        "password": "TestPassword123",
        "name": "Test User"
    }
    
    register_response = client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    # Now login
    login_data = {
        "email": "login-test@example.com",
        "password": "TestPassword123"
    }
    
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


def test_user_login_invalid_credentials(client: TestClient, db_session: Session):
    """Test login with invalid credentials."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_password_change(client: TestClient, db_session: Session):
    """Test password change functionality."""
    # First register and login
    user_data = {
        "email": "passchange-test@example.com",
        "password": "TestPassword123",
        "name": "Test User"
    }
    
    register_response = client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    login_response = client.post("/api/v1/auth/login", json={
        "email": "passchange-test@example.com",
        "password": "TestPassword123"
    })
    assert login_response.status_code == 200
    
    # Get access token
    access_token = login_response.json()["access_token"]
    
    # Change password
    password_change_data = {
        "current_password": "TestPassword123",
        "new_password": "NewPassword456"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/v1/auth/change-password", json=password_change_data, headers=headers)
    assert response.status_code == 200
    assert "Password changed successfully" in response.json()["message"]


def test_get_current_user(client: TestClient, db_session: Session):
    """Test getting current user information."""
    # First register and login
    user_data = {
        "email": "me-test@example.com",
        "password": "TestPassword123",
        "name": "Test User"
    }
    
    register_response = client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    login_response = client.post("/api/v1/auth/login", json={
        "email": "me-test@example.com",
        "password": "TestPassword123"
    })
    assert login_response.status_code == 200
    
    # Get access token
    access_token = login_response.json()["access_token"]
    
    # Get current user
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email"] == "me-test@example.com"
    assert "id" in data


def test_get_current_user_no_token(client: TestClient, db_session: Session):
    """Test getting current user without token."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_auth_status_authenticated(client: TestClient, db_session: Session):
    """Test authentication status when authenticated."""
    # First register and login
    user_data = {
        "email": "status-test@example.com",
        "password": "TestPassword123",
        "name": "Test User"
    }
    
    register_response = client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    login_response = client.post("/api/v1/auth/login", json={
        "email": "status-test@example.com",
        "password": "TestPassword123"
    })
    assert login_response.status_code == 200
    
    # Get access token
    access_token = login_response.json()["access_token"]
    
    # Check auth status
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/auth/status", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"] is not None
    assert data["user"]["email"] == "status-test@example.com"


def test_auth_status_not_authenticated(client: TestClient, db_session: Session):
    """Test authentication status when not authenticated."""
    response = client.get("/api/v1/auth/status")
    assert response.status_code == 200
    
    data = response.json()
    assert data["authenticated"] is False
    assert data.get("user") is None


def test_protected_endpoint_without_auth(client: TestClient, db_session: Session):
    """Test that protected endpoints require authentication."""
    response = client.post("/api/v1/parse-jd", json={
        "role": "Software Engineer",
        "jobDescription": "Test job description"
    })
    assert response.status_code == 401


def test_protected_endpoint_with_auth(client: TestClient, db_session: Session):
    """Test that protected endpoints work with authentication."""
    # First register and login
    user_data = {
        "email": "protected-test@example.com",
        "password": "TestPassword123",
        "name": "Test User"
    }
    
    register_response = client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    login_response = client.post("/api/v1/auth/login", json={
        "email": "protected-test@example.com",
        "password": "TestPassword123"
    })
    assert login_response.status_code == 200
    
    # Get access token
    access_token = login_response.json()["access_token"]
    
    # Test protected endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/v1/parse-jd", json={
        "role": "Software Engineer",
        "jobDescription": "Test job description"
    }, headers=headers)
    
    # This might fail due to AI service not being available, but should not be 401
    assert response.status_code != 401


def test_auth_service_password_hashing(db_session: Session):
    """Test password hashing in AuthService."""
    auth_service = AuthService(db_session)
    
    password = "TestPassword123"
    hashed = auth_service.get_password_hash(password)
    
    # Hash should be different from original password
    assert hashed != password
    
    # Should be able to verify the password
    assert auth_service.verify_password(password, hashed)
    
    # Should not verify wrong password
    assert not auth_service.verify_password("wrongpassword", hashed)


def test_auth_service_token_creation(db_session: Session):
    """Test JWT token creation and verification."""
    auth_service = AuthService(db_session)
    
    user_id = "test-user-id-123"
    email = "token-test@example.com"
    role = "user"
    
    # Create access token
    access_token = auth_service.create_access_token(user_id, email, role)
    assert access_token is not None
    
    # Verify token
    token_payload = auth_service.verify_token(access_token)
    assert token_payload is not None
    assert token_payload.sub == user_id
    assert token_payload.email == email
    assert token_payload.role == role


def test_auth_service_user_creation(db_session: Session):
    """Test user creation in AuthService."""
    auth_service = AuthService(db_session)
    
    email = "create-test@example.com"
    password = "TestPassword123"
    first_name = "Test"
    last_name = "User"
    
    # Create user
    user = auth_service.create_user(email, password, first_name, last_name)
    
    assert user is not None
    assert user.email == email
    assert user.name == "Test User"
    assert user.password_hash != password  # Should be hashed
    assert user.is_active is True
