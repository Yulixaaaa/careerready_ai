# src/modules/job_management.py

from sqlalchemy.orm import Session
from src.database.database import Job, User
from sqlalchemy import Float # Import Float if needed for other modules

def create_job(db: Session, user_id: int, job_title: str):
    """
    Creates a new job entry associated with a user.
    """
    # Basic validation: Check if user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None # Or raise an exception

    new_job = Job(job_title=job_title, user_id=user_id)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

def get_job_by_id(db: Session, job_id: int):
    """
    Retrieves a job posting by its ID.
    """
    return db.query(Job).filter(Job.job_id == job_id).first()

def get_jobs_by_user_id(db: Session, user_id: int, skip: int = 0, limit: int = 10):
    """
    Retrieves all job postings associated with a specific user.
    """
    return db.query(Job).filter(Job.user_id == user_id).offset(skip).limit(limit).all()

def update_job(db: Session, job_id: int, job_title: str = None):
    """
    Updates an existing job posting.
    """
    job = get_job_by_id(db, job_id)
    if not job:
        return None
    
    if job_title is not None:
        job.job_title = job_title
        
    db.commit()
    db.refresh(job)
    return job

def delete_job(db: Session, job_id: int):
    """
    Deletes a job posting.
    Note: Consider cascading deletes or handling related interviews/predictions.
    """
    job = get_job_by_id(db, job_id)
    if not job:
        return False
    
    # Handle related data (e.g., interviews, predictions) if necessary
    # Example: If interviews should be deleted when a job is deleted
    # db.query(Interview).filter(Interview.job_id == job_id).delete()
    # db.query(Prediction).filter(Prediction.interview_id.in_(
    #     db.query(Interview.interview_id).filter(Interview.job_id == job_id)
    # )).delete()

    db.delete(job)
    db.commit()
    return True