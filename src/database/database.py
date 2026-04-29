# src/database/database.py
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Float,
    Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Import settings (FIXED PATH — adjust if needed)
from src.config.settings import settings

# ==================================================
# DATABASE ENGINE
# ==================================================

engine = create_engine(settings.DATABASE_URL)

# Base class for models
Base = declarative_base()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==================================================
# DB SESSION DEPENDENCY
# ==================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================================================
# MODELS
# ==================================================

# -------------------------
# USER MODEL
# -------------------------
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    
    is_online = Column(Boolean, default=False)

    jobs = relationship("Job", back_populates="user")
    interviews = relationship("Interview", back_populates="user")
    predictions = relationship("Prediction", back_populates="user")


# -------------------------
# JOB MODEL
# -------------------------
class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)

    user_id = Column(Integer, ForeignKey("users.user_id"))
    user = relationship("User", back_populates="jobs")

    interviews = relationship("Interview", back_populates="job")


# -------------------------
# INTERVIEW MODEL
# -------------------------
class Interview(Base):
    __tablename__ = "interviews"

    interview_id = Column(Integer, primary_key=True, index=True)
    questions = Column(Text)

    user_id = Column(Integer, ForeignKey("users.user_id"))
    job_id = Column(Integer, ForeignKey("jobs.job_id"))

    # 🔥 ADD THESE HERE (IMPORTANT)
    status = Column(String, default="ongoing")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interviews")
    job = relationship("Job", back_populates="interviews")

    predictions = relationship(
        "Prediction",
        back_populates="interview",
        uselist=False
    )

# -------------------------
# PREDICTION MODEL
# -------------------------
class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    result = Column(Float)

    interview_id = Column(
        Integer,
        ForeignKey("interviews.interview_id"),
        unique=True
    )

    user_id = Column(Integer, ForeignKey("users.user_id"))

    interview = relationship("Interview", back_populates="predictions")
    user = relationship("User", back_populates="predictions")


# -------------------------
# ADMIN MODEL
# -------------------------
class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)


# ==================================================
# CREATE TABLES
# ==================================================

Base.metadata.create_all(bind=engine)