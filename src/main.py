from fastapi import FastAPI, Depends, HTTPException, Form, Request, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional
import sys, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.database.database import (
    get_db, Prediction, engine, Base, User, Interview, Job,
    AdminJob, AdminQuestion
)
from src.modules import user_management, job_management, interview_logic, admin_management
from src.modules.ai_model import ai_model

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareerReady AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR  = os.path.join(CURRENT_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ─── ONLINE THRESHOLD (seconds) ──────────────────────────────────────────────
# FIXED: Usa ra ka threshold para consistent sa backend
ONLINE_THRESHOLD_SECONDS = 60

# ─── Pages ──────────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

# ─── Auth ────────────────────────────────────────────────────────────────────
@app.post("/users/register")
def register_user(name: str = Form(...), email: str = Form(...),
                  password: str = Form(...), db: Session = Depends(get_db)):
    if user_management.get_user_by_email(db, email):
        raise HTTPException(400, "Email already registered")
    user = user_management.create_user(db, name, email, password)
    return {"status": "success", "user_id": user.user_id, "name": user.name}

@app.post("/users/login")
def login_user(email: str = Form(...), password: str = Form(...),
               db: Session = Depends(get_db)):
    user = user_management.get_user_by_email(db, email)
    if not user or not user_management.verify_password(password, user.password):
        raise HTTPException(401, "Invalid credentials")
    user.is_online   = True
    user.last_active = datetime.utcnow()
    db.commit()
    return {"user_id": user.user_id, "name": user.name}

# ─── Admin Auth ───────────────────────────────────────────────────────────────
@app.post("/admin/login")
def admin_login(email: str = Form(...), password: str = Form(...)):
    ADMIN_U = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_P = os.environ.get("ADMIN_PASSWORD", "admin123")
    if email == ADMIN_U and password == ADMIN_P:
        return {"status": "success"}
    raise HTTPException(401, "Invalid admin credentials")

# ─── Admin: Users ─────────────────────────────────────────────────────────────
@app.get("/admin/users")
def admin_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()
        now = datetime.utcnow()
        result = []

        for u in users:
            # FIXED: Consistent 60-second threshold
            is_online = False
            if u.last_active:
                secs = (now - u.last_active).total_seconds()
                is_online = secs < ONLINE_THRESHOLD_SECONDS
            else:
                is_online = bool(u.is_online) if u.is_online is not None else False

            # Safe interview count
            interview_count = db.query(Interview).filter(
                Interview.user_id == u.user_id,
                Interview.status == "completed"
            ).count()

            # Safe best score
            best_pred = (db.query(Prediction)
                           .filter(Prediction.user_id == u.user_id)
                           .order_by(Prediction.result.desc())
                           .first())

            final_score = 0
            if best_pred and best_pred.result is not None:
                try:
                    final_score = round(float(best_pred.result), 2)
                except:
                    final_score = 0

            result.append({
                "user_id":         u.user_id,
                "name":            u.name if u.name else "Unknown",
                "email":           u.email,
                "is_online":       is_online,
                "last_active":     u.last_active.isoformat() if u.last_active else None,
                "interview_count": interview_count,
                "best_score":      final_score,
            })

        return result

    except Exception as e:
        print(f"[ERROR] admin_users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return {"status": "deleted"}

# ─── Admin: Jobs + Questions ──────────────────────────────────────────────────
@app.get("/admin/jobs")
def get_admin_jobs(db: Session = Depends(get_db)):
    jobs = db.query(AdminJob).all()
    return [
        {
            "admin_job_id":   j.admin_job_id,
            "job_title":      j.job_title,
            "description":    j.description,
            "created_at":     j.created_at.isoformat() if j.created_at else None,
            "question_count": len(j.questions),
            "questions": [
                {"question_id": q.question_id, "question_text": q.question_text}
                for q in j.questions
            ]
        }
        for j in jobs
    ]

@app.post("/admin/jobs")
async def create_admin_job(request: Request, db: Session = Depends(get_db)):
    body        = await request.json()
    job_title   = body.get("job_title", "").strip()
    description = body.get("description", "").strip()
    questions   = body.get("questions", [])

    if not job_title:
        raise HTTPException(400, "job_title is required")

    admin_job = AdminJob(
        job_title=job_title,
        description=description,
        created_at=datetime.utcnow()
    )
    db.add(admin_job)
    db.flush()

    for q_text in questions:
        if q_text.strip():
            db.add(AdminQuestion(
                admin_job_id=admin_job.admin_job_id,
                question_text=q_text.strip(),
                created_at=datetime.utcnow()
            ))

    db.commit()
    db.refresh(admin_job)
    return {
        "status":         "created",
        "admin_job_id":   admin_job.admin_job_id,
        "job_title":      admin_job.job_title,
        "question_count": len(admin_job.questions)
    }

@app.post("/admin/jobs/{admin_job_id}/questions")
async def add_question_to_job(admin_job_id: int, request: Request,
                               db: Session = Depends(get_db)):
    body   = await request.json()
    q_text = body.get("question_text", "").strip()
    if not q_text:
        raise HTTPException(400, "question_text is required")
    job = db.query(AdminJob).filter(AdminJob.admin_job_id == admin_job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    q = AdminQuestion(admin_job_id=admin_job_id, question_text=q_text,
                      created_at=datetime.utcnow())
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"question_id": q.question_id, "question_text": q.question_text}

@app.delete("/admin/jobs/{admin_job_id}")
def delete_admin_job(admin_job_id: int, db: Session = Depends(get_db)):
    job = db.query(AdminJob).filter(AdminJob.admin_job_id == admin_job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    db.delete(job)
    db.commit()
    return {"status": "deleted"}

@app.delete("/admin/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    q = db.query(AdminQuestion).filter(AdminQuestion.question_id == question_id).first()
    if not q:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()
    return {"status": "deleted"}

# ─── Admin: Analytics ────────────────────────────────────────────────────────
@app.get("/admin/analytics")
def get_analytics(db: Session = Depends(get_db)):
    predictions  = db.query(Prediction).all()
    scores       = [round(float(p.result), 2) for p in predictions if p.result is not None]
    total_users  = db.query(User).count()
    now          = datetime.utcnow()

    # FIXED: Consistent 60-second threshold (same as /admin/users)
    online_users = sum(
        1 for u in db.query(User).all()
        if u.last_active and (now - u.last_active).total_seconds() < ONLINE_THRESHOLD_SECONDS
    )

    return {
        "total_interviews": len(scores),
        "average_score":    round(sum(scores) / len(scores), 2) if scores else 0,
        "highest_score":    round(max(scores), 2) if scores else 0,
        "lowest_score":     round(min(scores), 2) if scores else 0,
        "total_users":      total_users,
        "online_users":     online_users,
    }

@app.get("/admin/analytics/monthly")
def get_monthly_analytics(db: Session = Depends(get_db)):
    from sqlalchemy import extract
    current_year = datetime.utcnow().year

    interview_rows = (db.query(
            extract('month', Interview.created_at).label('month'),
            func.count(Interview.interview_id).label('count'),
            func.avg(Prediction.result).label('avg_score')
        )
        .outerjoin(Prediction, Prediction.interview_id == Interview.interview_id)
        .filter(extract('year', Interview.created_at) == current_year)
        .group_by('month')
        .all()
    )

    user_rows = (db.query(
            extract('month', User.last_active).label('month'),
            func.count(User.user_id).label('count')
        )
        .filter(extract('year', User.last_active) == current_year)
        .group_by('month')
        .all()
    )

    month_names   = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    interview_map = {int(r.month): {"count": r.count, "avg_score": round(float(r.avg_score), 2) if r.avg_score else 0} for r in interview_rows}
    user_map      = {int(r.month): r.count for r in user_rows}

    return [
        {
            "month":      month_names[m - 1],
            "interviews": interview_map.get(m, {}).get("count", 0),
            "avg_score":  interview_map.get(m, {}).get("avg_score", 0),
            "new_users":  user_map.get(m, 0),
        }
        for m in range(1, 13)
    ]

# ─── Jobs (user-facing) ───────────────────────────────────────────────────────
@app.get("/jobs/available")
def get_available_jobs(db: Session = Depends(get_db)):
    jobs = db.query(AdminJob).all()
    return [
        {
            "admin_job_id":   j.admin_job_id,
            "job_title":      j.job_title,
            "description":    j.description,
            "question_count": len(j.questions)
        }
        for j in jobs
    ]

@app.post("/jobs")
def create_job(user_id: int = Form(...), job_title: str = Form(...),
               admin_job_id: Optional[int] = Form(None),
               db: Session = Depends(get_db)):
    job = Job(user_id=user_id, job_title=job_title,
              admin_job_id=admin_job_id if admin_job_id else None)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.job_id, "job_title": job.job_title}

# ─── Interviews ───────────────────────────────────────────────────────────────
@app.post("/interviews")
def start_interview(user_id: int = Form(...), job_id: int = Form(...),
                    db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(400, "Invalid job")
    questions = interview_logic.get_random_questions(job.job_title, 5, db, user_id)
    interview = interview_logic.create_interview(db, user_id, job_id, questions)
    return {"interview_id": interview.interview_id, "questions": questions}

@app.post("/interviews/submit")
async def submit_answers(request: Request, interview_id: int = Form(...),
                         db: Session = Depends(get_db)):
    form    = await request.form()
    answers = {k: v for k, v in form.items() if k != "interview_id"}

    prediction, result = interview_logic.submit_and_analyze_answers(
        db=db, interview_id=interview_id, user_answers=answers, ai_model=ai_model
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(500, result["error"])

    return {
        "prediction":      round(float(result.get("score", 0)), 2),
        "feedback":        result.get("feedback", ""),
        "communication":   round(result.get("communication", 0)),
        "technical":       round(result.get("technical", 0)),
        "problem_solving": round(result.get("problem_solving", 0)),
        "confidence":      round(result.get("confidence", 0)),
    }

# ─── User History ─────────────────────────────────────────────────────────────
@app.get("/user/history")
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    return interview_logic.get_user_history(db, user_id)

# ─── Ping / Offline ───────────────────────────────────────────────────────────
@app.get("/user/ping")
def user_ping(user_id: int, db: Session = Depends(get_db)):
    """
    FIXED: Called every 30s from frontend to keep user marked online.
    Sets is_online=True and refreshes last_active timestamp.
    """
    user = user_management.get_user_by_id(db, user_id)
    if user:
        user.is_online   = True
        user.last_active = datetime.utcnow()
        db.commit()
    return {"status": "ok"}

@app.get("/user/offline")
def user_offline(user_id: int, db: Session = Depends(get_db)):
    """
    Called when user closes the tab/browser via beforeunload event.
    Sets is_online=False immediately.
    """
    user = user_management.get_user_by_id(db, user_id)
    if user:
        user.is_online   = False
        user.last_active = datetime.utcnow()
        db.commit()
    return {"status": "ok"}
