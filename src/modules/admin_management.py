from sqlalchemy.orm import Session
from src.modules import user_management, job_management, interview_logic
from src.database.database import User, Admin
from src.modules.user_management import get_password_hash


# =========================
# USERS
# =========================
def get_all_users(db: Session):
    users = db.query(User).all()
    return [
        {
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "is_online": u.is_online,
            "last_active": u.last_active
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


# =========================
# JOBS
# =========================
def get_all_jobs(db: Session):
    return job_management.get_jobs_by_user_id(db, user_id=None)


def delete_job(db: Session, job_id: int):
    return job_management.delete_job(db, job_id)


# =========================
# QUESTIONS
# =========================
def add_question(db: Session, question_data):
    return interview_logic.add_question(db, question_data)


def get_questions(db: Session, job_title: str = None):
    return interview_logic.get_questions(db, job_title)


def delete_question(db: Session, question_id: int):
    return interview_logic.delete_question(db, question_id)


# =========================
# ANALYTICS
# =========================
def get_interview_reports(db: Session):
    return interview_logic.get_all_interview_results(db)


# =========================
# ADMIN AUTH FIX
# =========================
def create_admin(db: Session, email: str, password: str, username: str = "Admin"):
    admin = Admin(
        username=username,
        password=get_password_hash(password)
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin