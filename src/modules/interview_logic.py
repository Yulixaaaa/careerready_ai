# src/modules/interview_logic.py
"""
Interview Logic
===============
Key changes:
- get_random_questions() ONLY returns questions from admin-created jobs (DB)
- If job_title has no admin job in DB → returns [] (empty list)
- sample_questions.json is NO LONGER used as a fallback to prevent
  unauthorized job titles from getting questions
- Callers must check for empty list and show an error to the user
"""

import json
import random
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from src.database.database import (
    Interview, Prediction, Job, User,
    AdminJob, AdminQuestion, JobRequest
)


# ─────────────────────────────────────────────────────────────
# QUESTION FETCHING — STRICT: admin DB only, no JSON fallback
# ─────────────────────────────────────────────────────────────

def get_questions_for_admin_job(db: Session, admin_job_id: int) -> List[str]:
    """
    Fetch questions for a specific admin_job_id.
    Returns [] if job not found or has no questions.
    """
    admin_job = db.query(AdminJob).filter(
        AdminJob.admin_job_id == admin_job_id
    ).first()

    if not admin_job or not admin_job.questions:
        return []

    return [q.question_text for q in admin_job.questions]


def get_questions_by_title(db: Session, job_title: str) -> List[str]:
    """
    Fetch questions by job title (case-insensitive match against admin_jobs).
    Returns [] if no matching admin job exists — never falls back to JSON.
    This is the ERROR HANDLER: if no match → [] → caller shows 'job not available'.
    """
    admin_job = db.query(AdminJob).filter(
        AdminJob.job_title.ilike(job_title.strip())
    ).first()

    if not admin_job or not admin_job.questions:
        return []

    questions = [q.question_text for q in admin_job.questions]
    random.shuffle(questions)
    return questions


def get_random_questions(
    job_title: str,
    total: int = 5,
    db: Session = None,
    user_id: int = None,
    admin_job_id: int = None
) -> List[str]:
    """
    Main question getter.
    Priority:
      1. Specific admin_job_id (from user selecting a job card)
      2. Title match in admin_jobs DB
      3. Returns [] — NEVER falls back to sample_questions.json
    """
    if not db:
        return []

    # Priority 1: by admin_job_id
    if admin_job_id:
        questions = get_questions_for_admin_job(db, admin_job_id)
        if questions:
            random.shuffle(questions)
            return questions[:total]

    # Priority 2: by title match
    if job_title:
        questions = get_questions_by_title(db, job_title)
        if questions:
            return questions[:total]

    # No match found → return empty (caller must handle this as an error)
    return []


def job_exists_in_admin_db(db: Session, job_title: str) -> bool:
    """Check if admin has set up this job title."""
    job = db.query(AdminJob).filter(
        AdminJob.job_title.ilike(job_title.strip())
    ).first()
    return job is not None and bool(job.questions)


# ─────────────────────────────────────────────────────────────
# INTERVIEW CRUD
# ─────────────────────────────────────────────────────────────

def create_interview(
    db: Session,
    user_id: int,
    job_id: int,
    questions: List[str]
) -> Interview:
    interview = Interview(
        user_id=user_id,
        job_id=job_id,
        questions=json.dumps(questions),
        status="ongoing",
        created_at=datetime.utcnow()
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def get_interview_by_id(db: Session, interview_id: int) -> Optional[Interview]:
    return db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()


def get_interview_questions(interview: Interview) -> List[str]:
    if not interview or not interview.questions:
        return []
    try:
        return json.loads(interview.questions)
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────
# SUBMIT & ANALYZE
# ─────────────────────────────────────────────────────────────

def submit_and_analyze_answers(
    db: Session,
    interview_id: int,
    user_answers: Dict[str, str],
    ai_model
):
    interview = get_interview_by_id(db, interview_id)
    if not interview:
        return None, {"error": "Interview not found"}

    questions = get_interview_questions(interview)
    if not questions:
        return None, {"error": "No questions found for this interview"}

    # Build analysis input: pair each question with its answer
    analysis_input  = []
    answers_to_save = {}

    for i, question in enumerate(questions):
        answer_key = f"q{i}"
        answer = (user_answers.get(answer_key) or "").strip()
        if not answer:
            answer = (user_answers.get(question) or "").strip()
        analysis_input.append({"question": question, "answer": answer})
        answers_to_save[question] = answer

    try:
        result = ai_model.analyze_interview_answers(analysis_input)

        score           = round(float(result.get("score",           0)), 2)
        communication   = round(float(result.get("communication",   0)), 2)
        technical       = round(float(result.get("technical",       0)), 2)
        problem_solving = round(float(result.get("problem_solving", 0)), 2)
        confidence      = round(float(result.get("confidence",      0)), 2)
        feedback        = result.get("feedback", "Analysis complete.")

        interview.answers = json.dumps(answers_to_save)
        interview.status  = "completed"

        prediction = Prediction(
            interview_id=interview_id,
            user_id=interview.user_id,
            result=score,
            feedback=feedback,
            communication=communication,
            technical=technical,
            problem_solving=problem_solving,
            confidence=confidence,
            created_at=datetime.utcnow()
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction, result

    except Exception as e:
        db.rollback()
        return None, {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# USER HISTORY
# ─────────────────────────────────────────────────────────────

def get_user_history(db: Session, user_id: int) -> List[Dict]:
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == user_id, Interview.status == "completed")
        .order_by(Interview.created_at.desc())
        .all()
    )

    history = []
    for interview in interviews:
        pred = interview.predictions
        job  = interview.job

        try:
            answers_dict = json.loads(interview.answers) if interview.answers else {}
        except Exception:
            answers_dict = {}

        try:
            questions_list = json.loads(interview.questions) if interview.questions else []
        except Exception:
            questions_list = []

        history.append({
            "interview_id":    interview.interview_id,
            "job_title":       job.job_title if job else "Unknown",
            "created_at":      interview.created_at.isoformat() if interview.created_at else None,
            "score":           round(pred.result, 2) if pred and pred.result is not None else None,
            "feedback":        pred.feedback if pred else None,
            "communication":   round(pred.communication,   2) if pred else 0,
            "technical":       round(pred.technical,       2) if pred else 0,
            "problem_solving": round(pred.problem_solving, 2) if pred else 0,
            "confidence":      round(pred.confidence,      2) if pred else 0,
            "questions":       questions_list,
            "answers":         answers_dict,
        })
    return history


# ─────────────────────────────────────────────────────────────
# ADMIN — ALL RESULTS
# ─────────────────────────────────────────────────────────────

def get_all_interview_results(db: Session) -> List[Dict]:
    predictions = db.query(Prediction).all()
    results = []
    for p in predictions:
        interview = p.interview
        user      = p.user
        job_title = ""
        if interview and interview.job:
            job_title = interview.job.job_title

        results.append({
            "prediction_id": p.prediction_id,
            "user_id":       p.user_id,
            "user_name":     user.name if user else "Unknown",
            "interview_id":  p.interview_id,
            "job_title":     job_title,
            "score":         round(p.result, 2) if p.result is not None else 0,
            "date":          p.created_at.isoformat() if p.created_at else None
        })
    return results


# ─────────────────────────────────────────────────────────────
# ADMIN QUESTION MANAGEMENT
# ─────────────────────────────────────────────────────────────

def add_question(db: Session, question_data: Dict) -> Optional[AdminQuestion]:
    """
    Add a question to an existing admin job.
    question_data = {"admin_job_id": int, "question_text": str}
    """
    admin_job_id  = question_data.get("admin_job_id")
    question_text = (question_data.get("question_text") or "").strip()

    if not admin_job_id or not question_text:
        return None

    q = AdminQuestion(
        admin_job_id=admin_job_id,
        question_text=question_text,
        created_at=datetime.utcnow()
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def get_questions(db: Session, job_title: str = None) -> List[Dict]:
    if job_title:
        job = db.query(AdminJob).filter(
            AdminJob.job_title.ilike(job_title)
        ).first()
        if job:
            return [
                {"id": q.question_id, "text": q.question_text}
                for q in job.questions
            ]
    return []


def delete_question(db: Session, question_id: int) -> bool:
    q = db.query(AdminQuestion).filter(
        AdminQuestion.question_id == question_id
    ).first()
    if q:
        db.delete(q)
        db.commit()
        return True
    return False


def get_prediction_by_interview_id(
    db: Session, interview_id: int
) -> Optional[Prediction]:
    return db.query(Prediction).filter(
        Prediction.interview_id == interview_id
    ).first()


def monitor_system(db: Session) -> Dict:
    return {
        "users":      db.query(User).count(),
        "jobs":       db.query(Job).count(),
        "interviews": db.query(Interview).count()
    }


# ─────────────────────────────────────────────────────────────
# JOB REQUEST MANAGEMENT
# ─────────────────────────────────────────────────────────────

def create_job_request(
    db: Session,
    user_id: int,
    job_title: str,
    reason: str = ""
) -> Optional[JobRequest]:
    """
    User requests a new job that doesn't exist in admin_jobs yet.
    Prevents duplicates per user.
    """
    existing = db.query(JobRequest).filter(
        JobRequest.user_id == user_id,
        JobRequest.job_title.ilike(job_title.strip())
    ).first()

    if existing:
        return None  # Duplicate — caller should return 409

    req = JobRequest(
        user_id=user_id,
        job_title=job_title.strip(),
        reason=reason.strip(),
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def get_job_requests_by_user(db: Session, user_id: int) -> List[Dict]:
    reqs = (
        db.query(JobRequest)
        .filter(JobRequest.user_id == user_id)
        .order_by(JobRequest.created_at.desc())
        .all()
    )
    return [
        {
            "request_id": r.request_id,
            "job_title":  r.job_title,
            "reason":     r.reason,
            "status":     r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reqs
    ]


def get_all_job_requests(db: Session) -> List[Dict]:
    """Admin: see all pending job requests."""
    reqs = (
        db.query(JobRequest)
        .order_by(JobRequest.created_at.desc())
        .all()
    )
    return [
        {
            "request_id": r.request_id,
            "user_id":    r.user_id,
            "user_name":  r.user.name if r.user else "Unknown",
            "job_title":  r.job_title,
            "reason":     r.reason,
            "status":     r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reqs
    ]


def update_job_request_status(
    db: Session,
    request_id: int,
    status: str  # "approved" | "declined"
) -> bool:
    req = db.query(JobRequest).filter(
        JobRequest.request_id == request_id
    ).first()
    if not req:
        return False
    req.status = status
    db.commit()
    return True