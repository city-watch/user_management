from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, get_db
from .models import models
from .models.user import (
    RegisterRequest,
    LoginRequest,
    RegisterResponse,
    LoginResponse,
    ProfileResponse,
    LeaderboardResponse,
    InternalEventRequest,
    InternalEventResponse,
    EventType,
    User
)
from .auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

POINTS_NEW_REPORT = 10
POINTS_CONFIRM_ISSUE = 5
POINTS_RESOLVED = 20

# -------------------------------------------------------
# FastAPI App Setup
# -------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before app startup
    models.Base.metadata.create_all(bind=engine)
    yield
    # After app shutdown (optional)
    # models.Base.metadata.drop_all(bind=engine) # if needed for cleanup

app = FastAPI(title="Civic User Management Service", version="1.0.0", lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# Root Endpoint
# -------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Civic User Management Service is running."}


# -------------------------------------------------------
#  Health Check Endpoints
# -------------------------------------------------------
@app.get("/health/live", tags=["Health"])
def liveness_check():
    """Liveness probe — confirms app process is alive."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe — verifies DB connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not ready: {e}",
        )

# -------------------------------------------------------
# USER & AUTHENTICATION ENDPOINTS
# -------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Decode JWT and fetch the current user."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = db.query(User).filter(
        User.user_id == payload.get("user_id")
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


# -------------------------------------------------------
# REGISTER
# -------------------------------------------------------
@app.post("/api/v1/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_pw = hash_password(payload.password)
    new_user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hashed_pw,
        role=payload.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "user_id": new_user.user_id,
        "email": new_user.email,
        "role": new_user.role
    })

    return RegisterResponse(
        user_id=new_user.user_id,
        name=new_user.name,
        email=new_user.email,
        role=new_user.role,
        token=token,
    )


# -------------------------------------------------------
#  LOGIN
# -------------------------------------------------------
@app.post("/api/v1/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and issue JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_access_token({
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role
    })

    return LoginResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        role=user.role,
        token=token,
    )

# -------------------------------------------------------
# PROFILE
# -------------------------------------------------------
@app.get("/api/v1/profile/me", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get the currently logged-in user's profile."""
    return ProfileResponse(
        user_id=current_user.user_id,
        name=current_user.name,
        email=current_user.email,
        total_points=current_user.total_points,
        spendable_points=current_user.spendable_points,
    )


# -------------------------------------------------------
# LEADERBOARD
# -------------------------------------------------------
@app.get("/api/v1/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(db: Session = Depends(get_db)):
    """Return the top 10 users ranked by total points."""
    users = (
        db.query(User)
        .order_by(User.total_points.desc())
        .limit(10)
        .all()
    )

    leaderboard = [
        {"rank": idx + 1, "name": u.name, "total_points": u.total_points}
        for idx, u in enumerate(users)
    ]
    return LeaderboardResponse(leaderboard=leaderboard)

# -------------------------------------------------------
# INTERNAL GAMIFICATION EVENT PROCESSING
# -------------------------------------------------------
@app.post("/internal/events")
def process_gamification_event(event: InternalEventRequest, db: Session = Depends(get_db)):
    """
    Internal endpoint called by Report Service.
    Updates user points based on the event type.
    """
    # 1. Find the user
    user = db.query(User).filter(User.user_id == event.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Calculate Points based on Logic
    points_awarded = 0
    
    if event.event_type == EventType.NEW_REPORT:
        points_awarded = POINTS_NEW_REPORT
    elif event.event_type == EventType.CONFIRM_ISSUE:
        points_awarded = POINTS_CONFIRM_ISSUE
    elif event.event_type == EventType.REPORT_RESOLVED:
        points_awarded = POINTS_RESOLVED
    else:
        # Log warning here if needed for unknown event types
        return {"message": "Unknown event type, no points awarded."}

    # 3. Update the User (Atomic update via ORM)
    user.total_points += points_awarded
    user.spendable_points += points_awarded
    
    db.commit()
    db.refresh(user)

    return InternalEventResponse(
        message="Event processed successfully", 
        user_id=user.user_id, 
        points_added=points_awarded,
        new_total=user.total_points
    )


# -------------------------------------------------------
# Database Connectivity Diagnostic
# -------------------------------------------------------
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    """Manually verify DB connectivity and list tables."""
    try:
        # Use SQLAlchemy inspector to be compatible with both SQLite (tests) and Postgres (prod)
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        return {"status": "connected", "tables": tables}
    except Exception as e:
        return {"status": "error", "details": str(e)}
