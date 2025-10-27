from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from .models import User





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
