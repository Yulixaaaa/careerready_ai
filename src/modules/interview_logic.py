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
        "teacher": "Teacher",
        "instructor": "Teacher",
        "nurse": "Nurse",
        "registered nurse": "Nurse",
        "doctor": "Doctor",
        "physician": "Doctor",
        "lawyer": "Lawyer",
        "attorney": "Lawyer",
        "civil engineer": "Civil Engineer",
        "electrical engineer": "Electrical Engineer",
        "electrical engineering": "Electrical Engineer",
    }
    return aliases.get(title, job_title.strip())


def get_random_questions(job_title: str, total: int = 5, db=None, user_id=None) -> List[str]:
    if db:
        admin_job = db.query(AdminJob).filter(
            AdminJob.job_title.ilike(job_title)
        ).first()
        if admin_job and admin_job.questions:
            db_questions = [q.question_text for q in admin_job.questions]
            if len(db_questions) >= total:
                random.shuffle(db_questions)
                return db_questions[:total]

    try:
        with open("src/data/sample_questions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Error loading questions:", e)
        data = {}

    if not data:
        return ["Tell me about yourself."]

    fixed_title = normalize_job_title(job_title)
    pool = data.get(fixed_title, []) or data.get("General", [])
    if not pool:
        return ["Tell me about yourself."]

    used_questions = set()
    if db and user_id:
        past = db.query(Interview).filter(Interview.user_id == user_id).all()
        for i in past:
            try:
                used_questions.update(json.loads(i.questions))
            except Exception:
                pass

    fresh = [q for q in pool if q not in used_questions]
    if len(fresh) < total:
        fresh = pool

    random.shuffle(fresh)
    return fresh[:total]


def create_interview(db: Session, user_id: int, job_id: int, questions: List[str]):
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


def get_interview_by_id(db: Session, interview_id: int):
    return db.query(Interview).filter(Interview.interview_id == interview_id).first()


def get_interview_questions(interview: Interview) -> List[str]:
    if not interview or not interview.questions:
        return []
    try:
        return json.loads(interview.questions)
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
        answer_key = f"q{i}"
        answer = user_answers.get(answer_key, "").strip()
        if not answer:
            answer = user_answers.get(question, "").strip()
        analysis_input.append({"question": question, "answer": answer})
        answers_to_save[question] = answer

    try:
        result = ai_model.analyze_interview_answers(analysis_input)

        score           = round(float(result.get("score", 0)), 2)
        communication   = round(float(result.get("communication", 0)), 2)
        technical       = round(float(result.get("technical", 0)), 2)
        problem_solving = round(float(result.get("problem_solving", 0)), 2)
        confidence      = round(float(result.get("confidence", 0)), 2)
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


def get_user_history(db: Session, user_id: int):
    interviews = db.query(Interview).filter(
        Interview.user_id == user_id,
        Interview.status == "completed"
    ).order_by(Interview.created_at.desc()).all()

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
            "score":           round(pred.result, 2) if pred and pred.result else None,
            "feedback":        pred.feedback if pred else None,
            "communication":   round(pred.communication, 2) if pred else 0,
            "technical":       round(pred.technical, 2) if pred else 0,
            "problem_solving": round(pred.problem_solving, 2) if pred else 0,
            "confidence":      round(pred.confidence, 2) if pred else 0,
            "questions":       questions_list,
            "answers":         answers_dict,
        })
    return history


def get_all_interview_results(db: Session):
    predictions = db.query(Prediction).all()
    return [
        {
            "prediction_id": p.prediction_id,
            "user_id":       p.user_id,
            "interview_id":  p.interview_id,
            "result":        round(p.result, 2) if p.result else 0,
            "created_at":    p.created_at.isoformat() if p.created_at else None
        }
        for p in predictions
    ]


def add_question(db: Session, question_data):
    pass

def get_questions(db: Session, job_title: str = None):
    if job_title:
        job = db.query(AdminJob).filter(AdminJob.job_title.ilike(job_title)).first()
        if job:
            return [{"id": q.question_id, "text": q.question_text} for q in job.questions]
    return []

def delete_question(db: Session, question_id: int):
    q = db.query(AdminQuestion).filter(AdminQuestion.question_id == question_id).first()
    if q:
        db.delete(q)
        db.commit()
    return True

def get_prediction_by_interview_id(db: Session, interview_id: int):
    return db.query(Prediction).filter(Prediction.interview_id == interview_id).first()

def monitor_system(db: Session):
    return {
        "users":      db.query(User).count(),
        "jobs":       db.query(Job).count(),
        "interviews": db.query(Interview).count()
    }