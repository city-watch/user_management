from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, get_db
from fastapi.security import OAuth2PasswordBearer
from database import engine, get_db
from models import models
from models.user import (
    RegisterRequest,
    LoginRequest,
    RegisterResponse,
    LoginResponse,
    ProfileResponse,
    LeaderboardResponse,
)
from auth_utils import hash_password, verify_password, create_access_token, decode_access_token

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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    user = db.query(models.User).filter(models.User.user_id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user



@app.post("/api/v1/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_pw = hash_password(payload.password)
    new_user = models.User(
        name=payload.name,
        email=payload.email,
        password=hashed_pw,
        role=payload.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"user_id": new_user.user_id, "email": new_user.email})

    return RegisterResponse(
        user_id=new_user.user_id,
        name=new_user.name,
        email=new_user.email,
        token=token
    )


@app.post("/api/v1/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"user_id": user.user_id, "email": user.email})

    return LoginResponse(
        user_id=user.user_id,
        name=user.name,
        role=user.role,
        token=token
    )


@app.get("/api/v1/profile/me", response_model=ProfileResponse)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return ProfileResponse(
        user_id=current_user.user_id,
        name=current_user.name,
        email=current_user.email,
        total_points=current_user.total_points,
        spendable_points=current_user.spendable_points
    )


@app.get("/api/v1/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.total_points.desc()).limit(10).all()

    leaderboard = []
    rank = 1
    for u in users:
        leaderboard.append({"rank": rank, "name": u.name, "total_points": u.total_points})
        rank += 1
    return LeaderboardResponse(leaderboard=leaderboard)


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