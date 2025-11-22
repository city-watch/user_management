import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# -------------------------------------------------------
# 🔧 FIX: Add Project Root to Path
# -------------------------------------------------------
# This ensures 'user_management' module is found regardless of where pytest is run
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Adjust these imports to match your folder structure
# If running from root: from user_management.main import app, get_db
from user_management.main import app, get_db
from user_management.models.models import Base
from user_management.models.user import User, EventType


# -------------------------------------------------------
# ⚙️ Test Database Setup
# -------------------------------------------------------
# Use in-memory SQLite for fast, isolated tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# -------------------------------------------------------
# 🧪 Fixtures
# -------------------------------------------------------
@pytest.fixture(scope="function")
def db_session():
    """Create a new database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables to ensure clean slate for next test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a new test client for each test with DB override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]


# -------------------------------------------------------
# ✅ General Endpoint Tests
# -------------------------------------------------------

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Civic User Management Service is running."}


def test_liveness_check(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_check(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_db_check(client):
    response = client.get("/db-check")
    assert response.status_code == 200
    assert response.json()["status"] == "connected"
    assert "users" in response.json()["tables"]


# -------------------------------------------------------
# 🔐 Auth Tests
# -------------------------------------------------------

def test_register_user_success(client):
    response = client.post(
        "/api/v1/register",
        json={"name": "Test User", "email": "test@example.com", "password": "password", "role": "citizen"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "token" in data


def test_register_user_duplicate_email(client, db_session):
    # Manually insert a user first
    user = User(name="Existing User", email="test@example.com", password_hash="hashedpassword", role="citizen")
    db_session.add(user)
    db_session.commit()

    # Try to register again
    response = client.post(
        "/api/v1/register",
        json={"name": "Another User", "email": "test@example.com", "password": "password", "role": "citizen"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}


def test_login_user_success(client, db_session):
    # Register user via API first to ensure password hashing works
    client.post(
        "/api/v1/register",
        json={"name": "Test User", "email": "test@example.com", "password": "password", "role": "citizen"},
    )
    
    response = client.post(
        "/api/v1/login",
        json={"email": "test@example.com", "password": "password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "token" in data


def test_login_user_invalid_credentials(client):
    response = client.post(
        "/api/v1/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


# -------------------------------------------------------
# 👤 Profile & Leaderboard Tests
# -------------------------------------------------------

def test_get_profile_success(client):
    # Register to get token
    register_res = client.post("/api/v1/register", json={"name": "Test User", "email": "test@example.com", "password": "password", "role": "citizen"})
    token = register_res.json()["token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/profile/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"


def test_get_profile_invalid_token(client):
    headers = {"Authorization": "Bearer invalidtoken"}
    response = client.get("/api/v1/profile/me", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_get_leaderboard(client, db_session):
    # Create manually populated users
    user1 = User(name="User One", email="user1@test.com", password_hash="hash1", total_points=100)
    user2 = User(name="User Two", email="user2@test.com", password_hash="hash2", total_points=200)
    db_session.add_all([user1, user2])
    db_session.commit()

    response = client.get("/api/v1/leaderboard")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["leaderboard"]) == 2
    # User 2 has more points, should be rank 1
    assert data["leaderboard"][0]["name"] == "User Two"
    assert data["leaderboard"][0]["rank"] == 1
    assert data["leaderboard"][0]["total_points"] == 200


# -------------------------------------------------------
# 🎮 Internal Gamification Event Tests
# -------------------------------------------------------

def test_process_gamification_event_new_report(client, db_session):
    user = User(name="Test User", email="test@example.com", password_hash="hashedpassword", role="citizen", total_points=0, spendable_points=0)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Note: We use .value to send the string "new_report"
    event = {"user_id": user.user_id, "event_type": EventType.NEW_REPORT.value}
    response = client.post("/internal/events", json=event)
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Event processed successfully"
    assert data["points_added"] == 10
    assert data["new_total"] == 10


def test_process_gamification_event_confirm_issue(client, db_session):
    user = User(name="Test User", email="test@example.com", password_hash="hashedpassword", role="citizen", total_points=10, spendable_points=10)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    event = {"user_id": user.user_id, "event_type": EventType.CONFIRM_ISSUE.value}
    response = client.post("/internal/events", json=event)
    
    assert response.status_code == 200
    data = response.json()
    assert data["points_added"] == 5
    assert data["new_total"] == 15


def test_process_gamification_event_report_resolved(client, db_session):
    user = User(name="Test User", email="test@example.com", password_hash="hashedpassword", role="citizen", total_points=15, spendable_points=15)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    event = {"user_id": user.user_id, "event_type": EventType.REPORT_RESOLVED.value}
    response = client.post("/internal/events", json=event)
    
    assert response.status_code == 200
    data = response.json()
    assert data["points_added"] == 20
    assert data["new_total"] == 35


def test_process_gamification_event_unknown_user(client):
    # Use a valid event type, but non-existent user
    event = {"user_id": 999, "event_type": EventType.NEW_REPORT.value}
    response = client.post("/internal/events", json=event)
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_process_gamification_event_invalid_event_type(client, db_session):
    """
    Since we moved to Pydantic Enums, sending an invalid string
    should raise a 422 Validation Error, NOT a 200 with a message.
    """
    user = User(name="Test User", email="test@example.com", password_hash="hashedpassword", role="citizen")
    db_session.add(user)
    db_session.commit()
    
    # Sending a string that is NOT in the Enum
    event = {"user_id": user.user_id, "event_type": "THIS_IS_NOT_A_VALID_EVENT"}
    response = client.post("/internal/events", json=event)
    
    # FastAPI automatically returns 422 Unprocessable Entity for schema violations
    assert response.status_code == 422