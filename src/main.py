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

from src.database.database import get_db, Prediction, User, Job, engine, Base
from src.modules import user_management, job_management, interview_logic, admin_management
from src.modules.ai_model import ai_model

# ===============================
# INIT DB
# ===============================
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareerReady AI", version="1.0.0")

# ===============================
# CORS
# ===============================
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
    return {"status": "success", "user_id": user.user_id}


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
    user.last_active = datetime.utcnow()
    db.commit()

    return {
        "user_id": user.user_id,
        "name": user.name,
        "status": "online"
    }


# ===============================
# ADMIN LOGIN
# ===============================
@app.post("/admin/login")
def admin_login(email: str = Form(...), password: str = Form(...)):
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    if email == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return {"status": "success", "redirect": "/admin"}

    raise HTTPException(status_code=401, detail="Invalid admin credentials")


# ===============================
# ADMIN USERS
# ===============================
@app.get("/admin/users")
def admin_users(db: Session = Depends(get_db)):
    return admin_management.get_all_users(db)


# ===============================
# ADMIN ANALYTICS (FIXED + ENHANCED)
# ===============================
@app.get("/admin/analytics")
def get_analytics(db: Session = Depends(get_db)):
    predictions = db.query(Prediction).all()

    scores = [p.result for p in predictions if p.result is not None]

    monthly = {}

    for p in predictions:
        if not p.created_at:
            continue
        month = p.created_at.strftime("%Y-%m")
        monthly.setdefault(month, []).append(p.result or 0)

    monthly_avg = {
        m: round(sum(v) / len(v), 2)
        for m, v in monthly.items()
    }

    return {
        "total_interviews": len(scores),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "highest_score": round(max(scores), 2) if scores else 0,
        "lowest_score": round(min(scores), 2) if scores else 0,

        # for charts
        "monthly_average": monthly_avg
    }


# ===============================
# JOBS
# ===============================
@app.post("/jobs")
def create_job(
    user_id: int = Form(...),
    job_title: str = Form(...),
    db: Session = Depends(get_db)
):
    job = job_management.create_job(db, user_id, job_title)

    if not job:
        raise HTTPException(status_code=400, detail="Invalid user")

    return {
        "job_id": job.job_id,
        "job_title": job.job_title
    }


@app.get("/jobs/all")
def get_all_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()

    return [
        {
            "job_id": j.job_id,
            "job_title": j.job_title,
            "user_id": j.user_id
        }
        for j in jobs
    ]


# ===============================
# INTERVIEWS
# ===============================
@app.post("/interviews")
def start_interview(
    user_id: int = Form(...),
    job_id: int = Form(...),
    db: Session = Depends(get_db)
):
    job = job_management.get_job_by_id(db, job_id)

    if not job:
        raise HTTPException(status_code=400, detail="Invalid job")

    questions = interview_logic.get_random_questions(
        job.job_title, 5, db, user_id
    )

    interview = interview_logic.create_interview(db, user_id, job_id, questions)

    return {
        "interview_id": interview.interview_id,
        "questions": questions
    }


@app.post("/interviews/submit")
async def submit_answers(
    request: Request,
    interview_id: int = Form(...),
    db: Session = Depends(get_db)
):
    form = await request.form()
    answers = {k: v for k, v in form.items() if k != "interview_id"}

    prediction, result = interview_logic.submit_and_analyze_answers(
        db=db,
        interview_id=interview_id,
        user_answers=answers,
        ai_model=ai_model
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "score": result.get("score", 0),
        "feedback": result.get("feedback", ""),
        "communication": result.get("communication", 0),
        "technical": result.get("technical", 0),
        "problem_solving": result.get("problem_solving", 0),
        "confidence": result.get("confidence", 0)
    }


# ===============================
# USER DASHBOARD API (NEW)
# ===============================
@app.get("/user/dashboard")
def user_dashboard(user_id: int, db: Session = Depends(get_db)):
    results = db.query(Prediction).filter(
        Prediction.user_id == user_id
    ).all()

    scores = [r.result for r in results if r.result]

    avg = round(sum(scores) / len(scores), 2) if scores else 0

    readiness = (
        "READY" if avg >= 75 else
        "IMPROVING" if avg >= 50 else
        "NEEDS IMPROVEMENT"
    )

    return {
        "total_attempts": len(results),
        "average_score": avg,
        "highest_score": max(scores) if scores else 0,
        "readiness": readiness,
        "history": [
            {
                "score": r.result,
                "feedback": r.feedback,
                "date": r.created_at
            }
            for r in results
        ]
    }


# ===============================
# ONLINE STATUS SYSTEM
# ===============================
@app.get("/user/ping")
def user_ping(user_id: int, db: Session = Depends(get_db)):
    user = user_management.get_user_by_id(db, user_id)

    if user:
        user.is_online = True
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