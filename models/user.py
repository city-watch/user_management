from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from enum import Enum


# -------------------------------
# SQLAlchemy ORM Model
# -------------------------------
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="Citizen")
    total_points = Column(Integer, default=0)
    spendable_points = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    issues = relationship("Issue", back_populates="reporter")


# -------------------------------
# Pydantic Schemas (for FastAPI)
# -------------------------------

# -------- Enums --------
class EventType(str, Enum):
    NEW_REPORT = "new_report"
    CONFIRM_ISSUE = "confirm_issue"
    REPORT_RESOLVED = "report_resolved"


# -------- Requests --------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "Citizen"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class InternalEventRequest(BaseModel):
    user_id: int
    event_type: EventType


# -------- Responses --------
class UserBase(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    role: Optional[str] = "Citizen"

    # Pydantic V2 Config
    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(UserBase):
    token: str


class LoginResponse(UserBase):
    token: str


class ProfileResponse(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    total_points: int
    spendable_points: int

    # Pydantic V2 Config
    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    total_points: int


class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]


class InternalEventResponse(BaseModel):
    message: str
    user_id: int
    points_added: int
    new_total: int