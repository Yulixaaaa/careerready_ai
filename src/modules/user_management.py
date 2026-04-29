from sqlalchemy.orm import Session
from src.database.database import User, Admin  # Gi-usa na ang pag-import
from passlib.context import CryptContext

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# ===============================
# USER LOGIC
# ===============================
def create_user(db: Session, name: str, email: str, password: str):
    hashed_password = get_password_hash(password)
    new_user = User(name=name, email=email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()

def get_all_users(db: Session):
    return db.query(User).all()

def delete_user(db: Session, user_id: int):
    user = get_user_by_id(db, user_id)
    if not user:
        return {"success": False, "message": "User not found"}
    db.delete(user)
    db.commit()
    return {"success": True, "message": "User deleted successfully"}

# ===============================
# ADMIN LOGIC
# ===============================
def create_admin_user(db: Session, username: str, password: str):
    hashed_password = get_password_hash(password)
    new_admin = Admin(username=username, password=hashed_password)
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin

def get_admin_by_username(db: Session, username: str):
    return db.query(Admin).filter(Admin.username == username).first()