from sqlalchemy.orm import Session
from src.modules import user_management, job_management, interview_logic
from src.database.database import User, Admin

# ===============================
# USER MANAGEMENT (ADMIN)
# ===============================
def get_all_users(db: Session):
    """Returns a list of users with online status for admin dashboard"""
    users = db.query(User).all()
    return [
        {
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "is_online": getattr(u, 'is_online', False) # Sigurado nga dili mo-error kung wala pay column
        }
        for u in users
    ]

def delete_user(db: Session, user_id: int):
    return user_management.delete_user(db, user_id)

# ===============================
# JOB / DATA MANAGEMENT
# ===============================
def get_all_jobs(db: Session):
    # Siguroha nga naa kay get_all_jobs sa job_management
    try:
        return job_management.get_all_jobs(db)
    except:
        return []

def delete_job(db: Session, job_id: int):
    return job_management.delete_job(db, job_id)

# ===============================
# QUESTIONS / DATASET
# ===============================
def add_question(db: Session, question_data):
    return interview_logic.add_question(db, question_data)

def get_questions(db: Session, job_title: str = None):
    return interview_logic.get_questions(db, job_title)

def delete_question(db: Session, question_id: int):
    return interview_logic.delete_question(db, question_id)

# ===============================
# REPORTS / ANALYTICS
# ===============================
def get_interview_reports(db: Session):
    return interview_logic.get_all_interview_results(db)

# ===============================
# ADMIN CREATION
# ===============================
def create_admin(db: Session, username: str, password: str):
    # Naggamit sa password hashing gikan sa user_management
    return user_management.create_admin_user(db, username, password)