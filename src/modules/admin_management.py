from sqlalchemy.orm import Session
from src.modules import user_management
from src.modules import job_management
from src.modules import interview_logic
from src.database.database import User


# ===============================
# USER MANAGEMENT (ADMIN)
# ===============================
def get_all_users(db: Session):
    users = user_management.get_all_users(db)

    return [
        {
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "is_online": u.is_online
        }
        for u in users
    ]


def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        return {"message": "User not found"}

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


# ===============================
# JOB MANAGEMENT
# ===============================
def get_all_jobs(db: Session):
    return job_management.get_all_jobs(db)


def delete_job(db: Session, job_id: int):
    return job_management.delete_job(db, job_id)


# ===============================
# QUESTIONS
# ===============================
def add_question(db: Session, question_data):
    return interview_logic.add_question(db, question_data)


def get_questions(db: Session, job_title: str = None):
    return interview_logic.get_questions(db, job_title)


def delete_question(db: Session, question_id: int):
    return interview_logic.delete_question(db, question_id)


# ===============================
# REPORTS
# ===============================
def get_interview_reports(db: Session):
    return interview_logic.get_all_interview_results(db)


# ===============================
# DATASET UPDATE
# ===============================
def update_dataset(db: Session, new_data):
    return {
        "message": "dataset updated",
        "data": new_data
    }