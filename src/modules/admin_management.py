# ===============================
# ADMIN MANAGEMENT MODULE
# CareerReady_AI
# ===============================

from sqlalchemy.orm import Session
from src.modules import user_management
from src.modules import job_management
from src.modules import interview_logic
from src.database.database import User

# ===============================
# USER MANAGEMENT (ADMIN)
# ===============================
def get_all_users(db: Session):
    return user_management.get_all_users(db)


def delete_user(db, user_id):
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        return {"message": "User not found"}

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}

def get_all_users(db):
    users = db.query(User).all()

    return [
        {
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "is_online": u.is_online   # 🔥 IMPORTANT
        }
        for u in users
    ]

# ===============================
# JOB / DATA MANAGEMENT
# ===============================
def get_all_jobs(db: Session):
    return job_management.get_all_jobs(db)


def delete_job(db: Session, job_id: int):
    return job_management.delete_job(db, job_id)


# ===============================
# QUESTIONS / DATASET
# ===============================
def add_question(db: Session, question_data):
    """
    Example: question_data = {
        "job_title": "Software Engineer",
        "question": "Tell me about yourself"
    }
    """
    return interview_logic.add_question(db, question_data)


def get_questions(db: Session, job_title: str = None):
    return interview_logic.get_questions(db, job_title)


def delete_question(db: Session, question_id: int):
    return interview_logic.delete_question(db, question_id)


# ===============================
# REPORTS / ANALYTICS
# ===============================
def get_interview_reports(db: Session):
    """
    Returns interview results / AI predictions summary
    """
    return interview_logic.get_all_interview_results(db)


# ===============================
# UPDATE DATASET (AI / QUESTIONS)
# ===============================
def update_dataset(db: Session, new_data):
    """
    Optional: update AI training or question dataset
    """
    # placeholder logic (depends sa imong AI design)
    return {
        "message": "dataset updated",
        "data": new_data
    }
def create_admin(db, email, password, name="Admin"):
    hashed_password = hash_password(password)

    admin = Admin(
        email=email,
        password=hashed_password,
        name=name
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin