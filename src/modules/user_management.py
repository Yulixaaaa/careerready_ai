import bcrypt
from sqlalchemy.orm import Session
from src.database.database import User


# =========================
# PASSWORD
# =========================
def get_password_hash(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(
        plain_password.encode(),
        hashed_password.encode()
    )


# =========================
# USER CRUD
# =========================
def create_user(db: Session, name: str, email: str, password: str):
    user = User(
        name=name,
        email=email,
        password=get_password_hash(password),
        is_online=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()


# ✅ ADD THIS (VERY IMPORTANT)
def get_all_users(db: Session):
    return db.query(User).all()


# =========================
# ONLINE STATUS
# =========================
def set_user_online(db: Session, user_id: int, status: bool):
    user = get_user_by_id(db, user_id)
    if user:
        user.is_online = status
        db.commit()
    return user