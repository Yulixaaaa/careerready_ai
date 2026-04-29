# src/modules/user_management.py

from sqlalchemy.orm import Session
from src.database.database import User # Import the User model
from passlib.context import CryptContext # For password hashing

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_user(db: Session, name: str, email: str, password: str):
    """
    Creates a new user in the database.
    """
    hashed_password = get_password_hash(password)
    new_user = User(name=name, email=email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_email(db: Session, email: str):
    """
    Retrieves a user by their email.
    """
    return db.query(User).filter(User.email == email).first()
def get_user_by_id(db, user_id):
    return db.query(User).filter(User.user_id == user_id).first()
def get_all_users(db: Session):
    """
    Returns all users in the system (Admin use only)
    """
    return db.query(User).all()
def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        return {
            "success": False,
            "message": "User not found"
        }

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": "User deleted successfully"
    }

def get_user_by_id(db: Session, user_id: int):
    """
    Retrieves a user by their ID.
    """
    return db.query(User).filter(User.user_id == user_id).first()

# Add functions for admin user management if needed
def create_admin_user(db: Session, username: str, password: str):
    """Creates a new admin user."""
    from src.database.database import Admin # Import Admin model
    hashed_password = get_password_hash(password)
    new_admin = Admin(username=username, password=hashed_password)
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin

def get_admin_by_username(db: Session, username: str):
    """Retrieves an admin user by username."""
    from src.database.database import Admin
    return db.query(Admin).filter(Admin.username == username).first()