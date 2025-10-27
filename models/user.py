from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base
from pydantic import BaseModel, EmailStr
from typing import List, Optional


# -------------------------------
# SQLAlchemy ORM Model
# -------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="Citizen")
    total_points = Column(Integer, default=0)
    spendable_points = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# -------------------------------
# Pydantic Schemas (for FastAPI)
# -------------------------------

# -------- Requests --------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "Citizen"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# -------- Responses --------
class UserBase(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    role: Optional[str] = "Citizen"

    class Config:
        orm_mode = True


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

    class Config:
        orm_mode = True


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    total_points: int


class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]
