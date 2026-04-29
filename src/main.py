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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.database.database import get_db, Prediction, engine, Base
from src.modules import user_management, job_management, interview_logic, admin_management
from src.modules.ai_model import ai_model

# DATABASE SETUP
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareerReady AI", version="1.0.0")

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
# Fixed pathing para sa Render deployment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(CURRENT_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

# ===============================
# REGISTER & LOGIN
# ===============================
@app.post("/users/register")
def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if user_management.get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = user_management.create_user(db, name, email, password)
    return {"status": "success", "user_id": user.user_id, "name": user.name}

@app.post("/users/login")
def login_user(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = user_management.get_user_by_email(db, email)
    if not user or not user_management.verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.is_online = True
    db.commit()
    return {"user_id": user.user_id, "name": user.name}

# ===============================
# ADMIN ENDPOINTS
# ===============================
@app.post("/admin/login")
def admin_login(email: str = Form(...), password: str = Form(...)):
    # Simple check para sa admin credentials
    if email == "admin" and password == "admin123":
        return {"status": "success", "redirect": "/admin"}
    raise HTTPException(status_code=401, detail="Invalid admin credentials")

@app.get("/admin/analytics")
def get_analytics(db: Session = Depends(get_db)):
    predictions = db.query(Prediction).all()
    scores = [p.result for p in predictions]
    return {
        "total_interviews": len(scores),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "highest_score": max(scores) if scores else 0,
        "lowest_score": min(scores) if scores else 0
    }

@app.get("/admin/users")
def admin_users(db: Session = Depends(get_db)):
    return admin_management.get_all_users(db)

# ===============================
# JOBS & INTERVIEWS
# ===============================
@app.post("/jobs")
def create_job(user_id: int = Form(...), job_title: str = Form(...), db: Session = Depends(get_db)):
    job = job_management.create_job(db, user_id, job_title)
    return {"job_id": job.job_id, "job_title": job.job_title}

@app.post("/interviews")
def start_interview(user_id: int = Form(...), job_id: int = Form(...), db: Session = Depends(get_db)):
    job = job_management.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=400, detail="Invalid job")

    questions = interview_logic.get_random_questions(job.job_title, 5, db, user_id)
    interview = interview_logic.create_interview(db, user_id, job_id, questions)
    return {"interview_id": interview.interview_id, "questions": questions}

@app.post("/interviews/submit")
async def submit_answers(request: Request, interview_id: int = Form(...), db: Session = Depends(get_db)):
    form = await request.form()
    answers = {k: v for k, v in form.items() if k != "interview_id"}
    
    prediction, feedback = interview_logic.submit_and_analyze_answers(
        db=db, interview_id=interview_id, user_answers=answers, ai_model=ai_model
    )
    return {"prediction": prediction.result if prediction else 0, "feedback": feedback}

@app.get("/user/ping")
def user_ping(user_id: int, db: Session = Depends(get_db)):
    user = user_management.get_user_by_id(db, user_id)
    if user:
        user.is_online = True
        db.commit()
    return {"status": "ok"}