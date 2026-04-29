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

from src.config.settings import settings

# ==================================================
# DATABASE ENGINE
# ==================================================
engine = create_engine(settings.DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================================================
# MODELS
# ==================================================

class User(Base):
    __tablename__ = "users"

    user_id   = Column(Integer, primary_key=True, index=True)
    name      = Column(String, index=True)
    email     = Column(String, unique=True, index=True)
    password  = Column(String)
    is_online = Column(Boolean, default=False)
    last_active = Column(DateTime, default=datetime.utcnow)

    jobs        = relationship("Job",        back_populates="user")
    interviews  = relationship("Interview",  back_populates="user")
    predictions = relationship("Prediction", back_populates="user")


class AdminJob(Base):
    """Jobs created by admin — users pick from these."""
    __tablename__ = "admin_jobs"

    admin_job_id = Column(Integer, primary_key=True, index=True)
    job_title    = Column(String, index=True)
    description  = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    questions = relationship("AdminQuestion", back_populates="admin_job",
                             cascade="all, delete-orphan")


class AdminQuestion(Base):
    """Questions attached to an AdminJob."""
    __tablename__ = "admin_questions"

    question_id  = Column(Integer, primary_key=True, index=True)
    admin_job_id = Column(Integer, ForeignKey("admin_jobs.admin_job_id"))
    question_text = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)

    admin_job = relationship("AdminJob", back_populates="questions")


class Job(Base):
    """User-created job sessions (linked to an AdminJob or custom)."""
    __tablename__ = "jobs"

    job_id    = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)
    user_id   = Column(Integer, ForeignKey("users.user_id"))

    # optional link to the admin-created job
    admin_job_id = Column(Integer, ForeignKey("admin_jobs.admin_job_id"), nullable=True)

    user       = relationship("User", back_populates="jobs")
    interviews = relationship("Interview", back_populates="job")


class Interview(Base):
    __tablename__ = "interviews"

    interview_id = Column(Integer, primary_key=True, index=True)
    questions    = Column(Text)   # JSON list of question strings
    answers      = Column(Text, nullable=True)   # JSON dict of answers
    status       = Column(String, default="completed")
    created_at   = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.user_id"))
    job_id  = Column(Integer, ForeignKey("jobs.job_id"))

    user = relationship("User", back_populates="interviews")
    job  = relationship("Job",  back_populates="interviews")

    predictions = relationship("Prediction", back_populates="interview",
                               uselist=False)


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    result        = Column(Float)   # overall score 0-100
    feedback      = Column(Text, nullable=True)

    # Performance breakdown
    communication   = Column(Float, default=0)
    technical       = Column(Float, default=0)
    problem_solving = Column(Float, default=0)
    confidence      = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    interview_id = Column(Integer, ForeignKey("interviews.interview_id"), unique=True)
    user_id      = Column(Integer, ForeignKey("users.user_id"))

    interview = relationship("Interview", back_populates="predictions")
    user      = relationship("User",      back_populates="predictions")


class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)


# ==================================================
# CREATE TABLES
# ==================================================
Base.metadata.create_all(bind=engine)