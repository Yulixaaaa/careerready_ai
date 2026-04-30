# src/modules/ai_model.py
import re
from typing import List, Dict, Any


class AIModel:
    def __init__(self):
        print("AI Model initialized")

    def analyze_interview_answers(self, data: List[Dict[str, str]]) -> Dict[str, Any]:
        if not data:
            return {"score": 0, "feedback": "No answers provided.",
                    "communication": 0, "technical": 0, "problem_solving": 0, "confidence": 0}

        answer_scores = []
        for item in data:
            question = item.get("question", "").strip()
            answer   = item.get("answer", "").strip()
            answer_scores.append(self._score_single_answer(question, answer))

        overall         = round(sum(s["score"] for s in answer_scores) / len(answer_scores), 2)
        communication   = round(self._dim(answer_scores, "communication"), 2)
        technical       = round(self._dim(answer_scores, "technical"), 2)
        problem_solving = round(self._dim(answer_scores, "problem_solving"), 2)
        confidence      = round(self._dim(answer_scores, "confidence"), 2)
        feedback        = self._generate_feedback(overall, answer_scores)

        return {
            "score": overall, "feedback": feedback,
            "communication": communication, "technical": technical,
            "problem_solving": problem_solving, "confidence": confidence
        }

    # ── single answer ──────────────────────────────────────────
    def _score_single_answer(self, question: str, answer: str) -> Dict:
        base = {"score": 0, "rejected": False, "reason": "",
                "communication": 0, "technical": 0, "problem_solving": 0, "confidence": 0}

        if not answer:
            base.update({"rejected": True, "reason": "empty"})
            return base

        word_count = len(answer.split())

        if word_count < 15:
            s = max(5, word_count * 2)
            base.update({"score": s, "rejected": True, "reason": "too_short",
                         "communication": s, "technical": s, "problem_solving": s, "confidence": s})
            return base

        if not self._is_english(answer):
            base.update({"score": 5, "rejected": True, "reason": "non_english",
                         "communication": 5, "technical": 5, "problem_solving": 5, "confidence": 5})
            return base

        length_score    = self._length_score(word_count)
        relevance_score = self._relevance_score(question, answer)
        vocab_score     = self._vocab_score(answer)

        score = round(min(max((length_score * 0.35) + (relevance_score * 0.45) + (vocab_score * 0.20), 10), 100), 2)
        comm  = round(min(length_score * 0.4 + vocab_score * 0.6, 100), 2)
        tech  = round(min(relevance_score * 1.05, 100), 2)
        prob  = round(min(relevance_score * 0.6 + vocab_score * 0.4, 100), 2)
        conf  = round(min(length_score * 0.5 + score * 0.5, 100), 2)

        base.update({"score": score, "reason": "ok",
                     "communication": comm, "technical": tech,
                     "problem_solving": prob, "confidence": conf})
        return base

    def _length_score(self, wc: int) -> float:
        if wc < 15:   return max(5, wc * 2)
        if wc < 30:   return 30 + (wc - 15) * 1.6
        if wc < 60:   return 54 + (wc - 30) * 0.7
        if wc < 100:  return 75 + (wc - 60) * 0.325
        if wc < 200:  return 88 + (wc - 100) * 0.07
        return min(100, 95 + (wc - 200) * 0.025)

    def _relevance_score(self, question: str, answer: str) -> float:
        q_lower = question.lower()
        a_lower = answer.lower()
        strong_kw = [
            "experience", "worked", "responsible", "team", "project", "managed",
            "developed", "created", "improved", "achieved", "learned", "skills",
            "knowledge", "ability", "problem", "solution", "approach", "strategy",
            "example", "situation", "result", "outcome", "challenge", "success",
            "goal", "collaborate", "communication", "deadline", "leadership",
            "technical", "analysis", "design", "implement", "test", "debug",
            "optimize", "research", "data", "performance"
        ]
        stopwords = {"what","when","where","which","that","this","with","have","your",
                     "would","could","tell","about","describe","explain","give","make",
                     "from","they","them","been","were","will"}

        q_words     = set(re.findall(r'\b[a-z]{4,}\b', q_lower)) - stopwords
        a_words     = set(re.findall(r'\b[a-z]{4,}\b', a_lower))
        strong_hits = sum(1 for kw in strong_kw if kw in a_lower)
        topic_hits  = len(q_words & a_words)

        strong_score = min(strong_hits / max(len(strong_kw) * 0.3, 1), 1.0) * 60
        topic_score  = min(topic_hits / max(len(q_words) * 0.4, 1), 1.0) * 40
        return min(max(strong_score + topic_score, 5), 100)

    def _vocab_score(self, answer: str) -> float:
        words = re.findall(r'\b[a-z]{3,}\b', answer.lower())
        if not words:
            return 0
        return min(len(set(words)) / len(words) * 125, 100)

    def _is_english(self, text: str) -> bool:
        ascii_chars  = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_alpha  = sum(1 for c in text if c.isalpha())
        if total_alpha == 0 or ascii_chars / total_alpha < 0.85:
            return False
        common_en = {"i","the","a","an","is","are","was","were","my","me","we","it",
                     "in","on","at","to","and","or","but","not","have","has","had",
                     "be","been","do","did","will","would","can","could","should",
                     "may","might","for","of","with","from","this","that","am",
                     "he","she","they","you","your","our","their","its"}
        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        if len(text.split()) >= 10 and len(words & common_en) == 0:
            return False
        return True

    def _dim(self, scores: List[Dict], key: str) -> float:
        vals = [s[key] for s in scores if key in s]
        return sum(vals) / len(vals) if vals else 0

    def _generate_feedback(self, overall: float, answer_scores: List[Dict]) -> str:
        parts = []
        short   = sum(1 for s in answer_scores if s.get("reason") == "too_short")
        non_eng = sum(1 for s in answer_scores if s.get("reason") == "non_english")
        empty   = sum(1 for s in answer_scores if s.get("reason") == "empty")

        if non_eng:
            parts.append(f"{non_eng} answer(s) detected as non-English and received very low scores. Please answer all questions in English.")
        if short:
            parts.append(f"{short} answer(s) were too short (under 15 words). Provide detailed, well-explained responses.")
        if empty:
            parts.append(f"{empty} question(s) were left unanswered.")

        if overall >= 85:
            parts.append("Excellent performance! Your answers were detailed, relevant, and well-structured. You demonstrated strong communication and technical knowledge.")
        elif overall >= 70:
            parts.append("Good performance. Your answers showed solid understanding. Try to include more specific examples and elaborate further on technical details.")
        elif overall >= 55:
            parts.append("Average performance. Some answers lacked depth or relevance. Focus on providing concrete examples and expanding your responses.")
        elif overall >= 35:
            parts.append("Below average. Many answers were too brief or lacked relevant content. Practice giving detailed, structured answers using the STAR method (Situation, Task, Action, Result).")
        else:
            parts.append("Needs significant improvement. Most answers were too short, off-topic, or not in English. Study the role requirements and aim for at least 50-100 words per answer.")

        return " ".join(parts)


ai_model = AIModel()