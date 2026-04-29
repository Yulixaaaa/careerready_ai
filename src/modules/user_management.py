import bcrypt
from sqlalchemy.orm import Session
from src.database.database import User

# Ganti sa karaan nga pwd_context
def get_password_hash(password: str):
    # Kinahanglan i-encode ang string padulong bytes
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str):
    try:
        password_byte = plain_password.encode('utf-8')
        hashed_byte = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_byte, hashed_byte)
    except Exception:
        return False

def create_user(db: Session, name: str, email: str, password: str):
    hashed_pwd = get_password_hash(password)
    new_user = User(
        name=name,
        email=email,
        password=hashed_pwd,
        is_online=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()