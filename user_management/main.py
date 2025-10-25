from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, get_db
from user_management.models import models
from user_management.models.user import RegisterRequest, LoginRequest, RegisterResponse, LoginResponse, ProfileResponse, LeaderboardResponse

app = FastAPI(title="Civic User Management Service", version="1.0.0")

# Create tables if not already created
models.Base.metadata.create_all(bind=engine)


# -------------------------------------------------------
# 🌐 Root Endpoint
# -------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Civic User Management Service is running."}


# -------------------------------------------------------
# ❤️ Health Check Endpoints (for Kubernetes)
# -------------------------------------------------------

@app.get("/health/live", tags=["Health"])
def liveness_check():
    """
    Liveness probe — verifies that the app process is up.
    Kubernetes calls this periodically to ensure the container isn't stuck.
    """
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe — checks if the app is ready to receive traffic.
    It verifies DB connectivity and critical dependencies.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not ready: {e}",
        )


# -------------------------------------------------------
# 🧍 USER & AUTHENTICATION ENDPOINTS
# -------------------------------------------------------

@app.post("/api/v1/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Creates a new user.
    Body: { "name": "...", "email": "...", "password": "...", "role": "Citizen" }
    Response (201): { "user_id": 123, "name": "...", "email": "...", "token": "..." }
    """
    pass


@app.post("/api/v1/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user and returns a token.
    Body: { "email": "...", "password": "..." }
    Response (200): { "user_id": 123, "name": "...", "role": "...", "token": "..." }
    """
    pass


@app.get("/api/v1/profile/me", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    """
    Gets the profile of the currently authenticated user.
    Auth: Requires authentication token.
    Response (200): { "user_id": 123, "name": "...", "email": "...", "total_points": 150, "spendable_points": 120 }
    """
    pass


@app.get("/api/v1/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(db: Session = Depends(get_db)):
    """
    Gets the public leaderboard, ranked by total_points.
    Response (200): { "leaderboard": [ { "rank": 1, "name": "User A", "total_points": 150 }, ... ] }
    """
    pass


# -------------------------------------------------------
# 🧩 Database Connectivity Diagnostic
# -------------------------------------------------------
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    """
    Manual endpoint to verify DB connectivity and list tables.
    Useful for debugging or monitoring.
    """
    try:
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        result = db.execute(query)
        tables = [row[0] for row in result]
        return {"status": "connected", "tables": tables}
    except Exception as e:
        return {"status": "error", "details": str(e)}
