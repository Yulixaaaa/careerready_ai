# src/modules/interview_logic.py
import json
import random
from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from src.database.database import Interview, Prediction, Job, User, AdminJob, AdminQuestion


def normalize_job_title(job_title: str) -> str:
    if not job_title:
        return "General"
    title = job_title.strip().lower()
    aliases = {
        "software engineer": "Software Developer",
        "software developer": "Software Developer",
        "web developer": "Software Developer",
        "programmer": "Software Developer",
        "teacher": "Teacher", "instructor": "Teacher",
        "nurse": "Nurse", "registered nurse": "Nurse",
        "doctor": "Doctor", "physician": "Doctor",
        "lawyer": "Lawyer", "attorney": "Lawyer",
        "civil engineer": "Civil Engineer",
        "electrical engineer": "Electrical Engineer",
        "electrical engineering": "Electrical Engineer",
    }
    return aliases.get(title, job_title.strip())


def get_random_questions(job_title: str, total: int = 5, db=None, user_id=None) -> List[str]:
    # 1. Pull from AdminJob questions first
    if db:
        admin_job = db.query(AdminJob).filter(AdminJob.job_title.ilike(job_title)).first()
        if admin_job and admin_job.questions:
            db_qs = [q.question_text for q in admin_job.questions]
            if len(db_qs) >= total:
                random.shuffle(db_qs)
                return db_qs[:total]
            elif db_qs:
                return db_qs  # return all if fewer than total

    # 2. Fallback to JSON
    try:
        with open("src/data/sample_questions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    if not data:
        return ["Tell me about yourself."]

    pool = data.get(normalize_job_title(job_title), []) or data.get("General", [])
    if not pool:
        return ["Tell me about yourself."]

    used = set()
    if db and user_id:
        for i in db.query(Interview).filter(Interview.user_id == user_id).all():
            try:
                used.update(json.loads(i.questions))
            except Exception:
                pass

    fresh = [q for q in pool if q not in used] or pool
    random.shuffle(fresh)
    return fresh[:total]


def create_interview(db: Session, user_id: int, job_id: int, questions: List[str]):
    interview = Interview(
        user_id=user_id, job_id=job_id,
        questions=json.dumps(questions),
        status="ongoing", created_at=datetime.utcnow()
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def get_interview_by_id(db: Session, interview_id: int):
    return db.query(Interview).filter(Interview.interview_id == interview_id).first()


def get_interview_questions(interview: Interview) -> List[str]:
    try:
        return json.loads(interview.questions) if interview and interview.questions else []
    except Exception:
        return []


def submit_and_analyze_answers(db: Session, interview_id: int, user_answers: Dict[str, str], ai_model):
    interview = get_interview_by_id(db, interview_id)
    if not interview:
        return None, {"error": "Interview not found"}

    questions = get_interview_questions(interview)
    analysis_input = []
    answers_to_save = {}

    for i, question in enumerate(questions):
        answer = user_answers.get(f"q{i}", "").strip() or user_answers.get(question, "").strip()
        analysis_input.append({"question": question, "answer": answer})
        answers_to_save[question] = answer

    try:
        result          = ai_model.analyze_interview_answers(analysis_input)
        score           = round(float(result.get("score", 0)), 2)
        communication   = round(float(result.get("communication", 0)), 2)
        technical       = round(float(result.get("technical", 0)), 2)
        problem_solving = round(float(result.get("problem_solving", 0)), 2)
        confidence      = round(float(result.get("confidence", 0)), 2)
        feedback        = result.get("feedback", "Analysis complete.")

        interview.answers  = json.dumps(answers_to_save)
        interview.status   = "completed"

        prediction = Prediction(
            interview_id=interview_id, user_id=interview.user_id,
            result=score, feedback=feedback,
            communication=communication, technical=technical,
            problem_solving=problem_solving, confidence=confidence,
            created_at=datetime.utcnow()
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction, result

    except Exception as e:
        db.rollback()
        return None, {"error": str(e)}


def get_user_history(db: Session, user_id: int):
    # Include ALL interviews regardless of status so old records still show up
    interviews = (db.query(Interview)
                    .filter(Interview.user_id == user_id)
                    .order_by(Interview.created_at.desc()).all())
    history = []
    for iv in interviews:
        pred = iv.predictions
        job  = iv.job
        try:
            answers_dict   = json.loads(iv.answers)   if iv.answers   else {}
        except Exception:
            answers_dict   = {}
        try:
            questions_list = json.loads(iv.questions) if iv.questions else []
        except Exception:
            questions_list = []

        def _s(val):
            try:
                return round(float(val), 2) if val is not None else 0
            except Exception:
                return 0

        history.append({
            "interview_id":    iv.interview_id,
            "job_title":       job.job_title if job else "Unknown",
            "created_at":      iv.created_at.isoformat() if iv.created_at else None,
            "score":           _s(pred.result)                               if pred else 0,
            "feedback":        getattr(pred, "feedback", "") or ""           if pred else "",
            "communication":   _s(getattr(pred, "communication", 0))        if pred else 0,
            "technical":       _s(getattr(pred, "technical", 0))            if pred else 0,
            "problem_solving": _s(getattr(pred, "problem_solving", 0))      if pred else 0,
            "confidence":      _s(getattr(pred, "confidence", 0))           if pred else 0,
            "questions":       questions_list,
            "answers":         answers_dict,
        })
    return history


def get_all_interview_results(db: Session):
    return [
        {"prediction_id": p.prediction_id, "user_id": p.user_id,
         "interview_id": p.interview_id,
         "result": round(p.result, 2) if p.result else 0,
         "created_at": p.created_at.isoformat() if p.created_at else None}
        for p in db.query(Prediction).all()
    ]


# -- stubs kept for admin_management compatibility --
def add_question(db, question_data): pass

def get_questions(db, job_title=None):
    if job_title:
        job = db.query(AdminJob).filter(AdminJob.job_title.ilike(job_title)).first()
        if job:
            return [{"id": q.question_id, "text": q.question_text} for q in job.questions]
    return []

def delete_question(db, question_id):
    q = db.query(AdminQuestion).filter(AdminQuestion.question_id == question_id).first()
    if q:
        db.delete(q)
        db.commit()
    return True

def get_prediction_by_interview_id(db, interview_id):
    return db.query(Prediction).filter(Prediction.interview_id == interview_id).first()

def monitor_system(db):
    return {"users": db.query(User).count(), "jobs": db.query(Job).count(),
            "interviews": db.query(Interview).count()}