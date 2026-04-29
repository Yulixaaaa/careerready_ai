# ===============================
# src/modules/interview_logic.py
# ===============================

import json
import random
from typing import List, Dict
from sqlalchemy.orm import Session

from src.database.database import Interview, Prediction, Job, User


# ==============================
# LOAD QUESTIONS
# ==============================
def load_sample_questions(
    filepath: str = "src/data/sample_questions.json"
) -> Dict[str, List[str]]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error loading questions:", e)
        return {}


# ==============================
# NORMALIZE JOB TITLE
# ==============================
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


# ==============================
# GET RANDOM 10 QUESTIONS
# ==============================
def get_random_questions(job_title: str, total: int = 10, db=None, user_id=None) -> List[str]:
    data = load_sample_questions()

    if not data:
        return ["Tell me about yourself"]

    fixed_title = normalize_job_title(job_title)

    # 1. Get base questions
    pool = data.get(fixed_title, []) or data.get("General", [])

    if not pool:
        return ["Tell me about yourself"]

    # 2. Collect used questions from past interviews
    used_questions = set()

    if db and user_id:
        past_interviews = db.query(Interview).filter(
            Interview.user_id == user_id
        ).all()

        for i in past_interviews:
            try:
                used = json.loads(i.questions)
                used_questions.update(used)
            except:
                pass

    # 3. Remove already used questions
    fresh_pool = [q for q in pool if q not in used_questions]

    # 4. fallback if everything was used
    if len(fresh_pool) < total:
        fresh_pool = pool

    random.shuffle(fresh_pool)

    return fresh_pool[:total]


# ==============================
# CREATE INTERVIEW
# ==============================
def create_interview(
    db: Session,
    user_id: int,
    job_id: int,
    questions: List[str]
):
    interview = Interview(
        user_id=user_id,
        job_id=job_id,
        questions=json.dumps(questions)
    )

    db.add(interview)
    db.commit()
    db.refresh(interview)

    return interview


# ==============================
# GET INTERVIEW
# ==============================
def get_interview_by_id(db: Session, interview_id: int):
    return db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()


# ==============================
# GET QUESTIONS
# ==============================
def get_interview_questions(interview: Interview) -> List[str]:
    if not interview or not interview.questions:
        return []

    try:
        return json.loads(interview.questions)
    except:
        return []


# ==============================
# SUBMIT + AI ANALYSIS
# ==============================
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

    analysis_input = []

    for q in questions:
        analysis_input.append({
            "question": q,
            "answer": user_answers.get(q, "")
        })

    try:
        result = ai_model.analyze_interview_answers(analysis_input)

        score = float(result.get("score", 0))

        prediction = Prediction(
            interview_id=interview_id,
            user_id=interview.user_id,
            result=score
        )

        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        return prediction, result.get(
            "feedback",
            "Interview analysis complete."
        )

    except Exception as e:
        db.rollback()
        return None, {"error": str(e)}


# ==============================
# GET PREDICTION
# ==============================
def get_prediction_by_interview_id(
    db: Session,
    interview_id: int
):
    return db.query(Prediction).filter(
        Prediction.interview_id == interview_id
    ).first()


# ==============================
# ADMIN MONITOR
# ==============================
def monitor_system(db: Session):
    return {
        "users": db.query(User).count(),
        "jobs": db.query(Job).count(),
        "interviews": db.query(Interview).count()
    }