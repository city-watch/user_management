# models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DECIMAL, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from .user import User

class Issue(Base):
    __tablename__ = "issues"

    issue_id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.user_id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    latitude = Column(DECIMAL(10,8), nullable=False)
    longitude = Column(DECIMAL(11,8), nullable=False)
    image_url = Column(String(1024))
    category = Column(String(100))
    status = Column(String(50), default="submitted")
    priority = Column(String(50), default="low")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    reporter = relationship("User", back_populates="issues")
    comments = relationship("Comment", back_populates="issue", cascade="all, delete")
    confirmations = relationship("Confirmation", back_populates="issue", cascade="all, delete")

class Comment(Base):
    __tablename__ = "comments"

    comment_id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.issue_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    text = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    issue = relationship("Issue", back_populates="comments")

class Confirmation(Base):
    __tablename__ = "confirmations"

    confirmation_id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.issue_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(TIMESTAMP, server_default=func.now())

    issue = relationship("Issue", back_populates="confirmations")