from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import sys
import os

# ===============================
# PATH CONFIGURATION
# ===============================
# Siguraduhon nga mabasa ang tanang folders
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Import sa imong database ug models
from src.database.database import get_db, Prediction, engine, Base
from src.modules import user_management, job_management, interview_logic, admin_management
from src.modules.ai_model import ai_model

# ===============================
# DATABASE SETUP (THE FIX)
# ===============================
# Kini ang moseguro nga mahimo ang tables sa Render database inig start
Base.metadata.create_all(bind=engine)

# ===============================
# APP INITIALIZATION
# ===============================
app = FastAPI(
    title="CareerReady AI",
    description="Interview Success Prediction System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ===============================
# STATIC FILES
# ===============================
STATIC_DIR = os.path.join("src", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

db_dependency = Depends(get_db)

# ===============================
# ADMIN LOGIN
# ===============================
@app.post("/admin/login")
def admin_login(email: str = Form(...), password: str = Form(...)):
    # Simple check para sa admin credentials
    # Pwede nimo ni usbon kung gusto nimo i-check sa database
    if email == "admin" and password == "admin123":
        return {"admin_id": 1, "name": "Admin", "role": "admin"}
    
    raise HTTPException(status_code=401, detail="Invalid admin credentials")

# ===============================
# ADMIN ANALYTICS
# ===============================
@app.get("/admin/analytics")
def get_analytics(db: Session = Depends(get_db)):
    predictions = db.query(Prediction).all()
    scores = [p.result for p in predictions]

    if not scores:
        return {
            "total_interviews": 0,
            "average_score": 0,
            "highest_score": 0,
            "lowest_score": 0
        }

    return {
        "total_interviews": len(scores),
        "average_score": round(sum(scores) / len(scores), 2),
        "highest_score": max(scores),
        "lowest_score": min(scores)
    }

# ===============================
# USER TRACKING
# ===============================
@app.get("/user/ping")
def user_ping(user_id: int, db: Session = Depends(get_db)):
    user = user_management.get_user_by_id(db, user_id)
    if user:
        user.is_online = True
        # Siguraduhon nga naa kay last_active column sa database.py User model
        if hasattr(user, 'last_active'):
            user.last_active = datetime.utcnow()
        db.commit()
    return {"status": "ok"}

@app.get("/user/offline")
def user_offline(user_id: int, db: Session = Depends(get_db)):
    user = user_management.get_user_by_id(db, user_id)
    if user:
        user.is_online = False
        db.commit()
    return {"status": "offline"}

# ===============================
# ADMIN USER MANAGEMENT
# ===============================
@app.get("/admin/users")
def admin_users(db: Session = db_dependency):
    return admin_management.get_all_users(db)

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = db_dependency):
    return admin_management.delete_user(db, user_id)

# ===============================
# REGISTER & LOGIN
# ===============================
@app.post("/users/register")
def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = db_dependency
):
    if user_management.get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = user_management.create_user(db, name, email, password)
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email
    }

@app.post("/users/login")
def login_user(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = db_dependency
):
    user = user_management.get_user_by_email(db, email)
    if not user or not user_management.verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.is_online = True
    if hasattr(user, 'last_active'):
        user.last_active = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email
    }

# ===============================
# JOBS & INTERVIEWS
# ===============================
@app.post("/jobs")
def create_job(user_id: int = Form(...), job_title: str = Form(...), db: Session = db_dependency):
    job = job_management.create_job(db, user_id, job_title)
    return {"job_id": job.job_id, "job_title": job.job_title}

@app.get("/jobs/{user_id}")
def get_jobs(user_id: int, db: Session = db_dependency):
    jobs = job_management.get_jobs_by_user_id(db, user_id)
    return [{"job_id": j.job_id, "job_title": j.job_title} for j in jobs]

@app.post("/interviews")
def start_interview(user_id: int = Form(...), job_id: int = Form(...), db: Session = db_dependency):
    job = job_management.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=400, detail="Invalid job")

    questions = interview_logic.get_random_questions(job.job_title, 10, db, user_id)
    interview = interview_logic.create_interview(db, user_id, job_id, questions)
    interview.status = "ongoing"
    db.commit()

    return {"interview_id": interview.interview_id, "questions": questions}

@app.post("/interviews/submit")
async def submit_answers(request: Request, interview_id: int = Form(...), db: Session = db_dependency):
    interview = interview_logic.get_interview_by_id(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    form = await request.form()
    answers = {key: form[key] for key in form.keys()}

    prediction, feedback = interview_logic.submit_and_analyze_answers(
        db=db, interview_id=interview_id, user_answers=answers, ai_model=ai_model
    )

    interview.status = "completed"
    db.commit()

    user = user_management.get_user_by_id(db, interview.user_id)
    if user:
        user.is_online = False
        db.commit()

    return {
        "prediction": prediction.result if prediction else 0,
        "feedback": feedback
    }