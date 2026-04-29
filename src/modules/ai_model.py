import re
from typing import List, Dict, Any


class AIModel:
    def __init__(self):
        print("AI Model initialized")

    # ==========================================
    # MAIN ENTRY POINT
    # ==========================================
    def analyze_interview_answers(self, data: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyzes interview answers and returns a realistic score based on:
        - Answer length (short answers = low score)
        - English language detection (non-English = rejected / penalized)
        - Keyword relevance to the question
        - Overall quality
        """
        if not data:
            return {
                "score": 0,
                "feedback": "No answers provided.",
                "communication": 0,
                "technical": 0,
                "problem_solving": 0,
                "confidence": 0
            }

        answer_scores = []
        rejection_flags = []

        for item in data:
            question = item.get("question", "").strip()
            answer = item.get("answer", "").strip()

            result = self._score_single_answer(question, answer)
            answer_scores.append(result)

            if result["rejected"]:
                rejection_flags.append(question)

        # --- Overall score ---
        if not answer_scores:
            overall = 0
        else:
            raw_avg = sum(s["score"] for s in answer_scores) / len(answer_scores)
            overall = round(min(max(raw_avg, 0), 100), 2)

        # --- Per-dimension scores ---
        communication   = round(self._dimension_score(answer_scores, "communication"), 2)
        technical       = round(self._dimension_score(answer_scores, "technical"), 2)
        problem_solving = round(self._dimension_score(answer_scores, "problem_solving"), 2)
        confidence      = round(self._dimension_score(answer_scores, "confidence"), 2)

        # --- Feedback ---
        feedback = self._generate_feedback(overall, rejection_flags, answer_scores)

        return {
            "score": overall,
            "feedback": feedback,
            "communication": communication,
            "technical": technical,
            "problem_solving": problem_solving,
            "confidence": confidence
        }

    # ==========================================
    # SCORE A SINGLE ANSWER
    # ==========================================
    def _score_single_answer(self, question: str, answer: str) -> Dict:
        base = {
            "score": 0,
            "rejected": False,
            "communication": 0,
            "technical": 0,
            "problem_solving": 0,
            "confidence": 0,
            "reason": ""
        }

        # --- Empty answer ---
        if not answer:
            base["rejected"] = True
            base["reason"] = "empty"
            return base

        # --- Minimum length: at least 15 words ---
        word_count = len(answer.split())
        if word_count < 15:
            base["score"] = max(5, word_count * 2)   # tiny partial credit
            base["rejected"] = True
            base["reason"] = "too_short"
            base["communication"]   = base["score"]
            base["technical"]       = base["score"]
            base["problem_solving"] = base["score"]
            base["confidence"]      = base["score"]
            return base

        # --- English detection ---
        if not self._is_english(answer):
            base["score"] = 5
            base["rejected"] = True
            base["reason"] = "non_english"
            base["communication"]   = 5
            base["technical"]       = 5
            base["problem_solving"] = 5
            base["confidence"]      = 5
            return base

        # --- Length scoring (15–300+ words) ---
        length_score = self._length_score(word_count)

        # --- Keyword relevance ---
        relevance_score = self._relevance_score(question, answer)

        # --- Vocabulary richness ---
        vocab_score = self._vocab_score(answer)

        # --- Combine into overall answer score ---
        raw = (length_score * 0.35) + (relevance_score * 0.45) + (vocab_score * 0.20)
        score = round(min(max(raw, 10), 100), 2)

        # --- Per-dimension breakdown ---
        comm  = round(min((length_score * 0.4 + vocab_score * 0.6), 100), 2)
        tech  = round(min(relevance_score * 1.05, 100), 2)
        prob  = round(min((relevance_score * 0.6 + vocab_score * 0.4), 100), 2)
        conf  = round(min((length_score * 0.5 + score * 0.5), 100), 2)

        base.update({
            "score": score,
            "communication": comm,
            "technical": tech,
            "problem_solving": prob,
            "confidence": conf,
            "reason": "ok"
        })
        return base

    # ==========================================
    # LENGTH SCORING
    # ==========================================
    def _length_score(self, word_count: int) -> float:
        """
        15-29 words  → 30–54  (acceptable but weak)
        30-59 words  → 55–74  (decent)
        60-99 words  → 75–88  (good)
        100-199 words→ 89–95  (very good)
        200+ words   → 95–100 (excellent)
        """
        if word_count < 15:
            return max(5, word_count * 2)
        elif word_count < 30:
            return 30 + (word_count - 15) * 1.6
        elif word_count < 60:
            return 54 + (word_count - 30) * 0.7
        elif word_count < 100:
            return 75 + (word_count - 60) * 0.325
        elif word_count < 200:
            return 88 + (word_count - 100) * 0.07
        else:
            return min(100, 95 + (word_count - 200) * 0.025)

    # ==========================================
    # KEYWORD RELEVANCE
    # ==========================================
    def _relevance_score(self, question: str, answer: str) -> float:
        """
        Checks if the answer contains words/concepts relevant to the question.
        """
        question_lower = question.lower()
        answer_lower   = answer.lower()

        # General interview keywords that always matter
        strong_keywords = [
            "experience", "worked", "responsible", "team", "project",
            "managed", "developed", "created", "improved", "achieved",
            "learned", "skills", "knowledge", "ability", "problem",
            "solution", "approach", "strategy", "example", "situation",
            "result", "outcome", "challenge", "success", "goal",
            "collaborate", "communication", "deadline", "leadership",
            "technical", "analysis", "design", "implement", "test",
            "debug", "optimize", "research", "data", "performance"
        ]

        # Topic-specific keywords extracted from the question
        q_words = set(re.findall(r'\b[a-z]{4,}\b', question_lower))
        # Remove filler words
        stopwords = {"what", "when", "where", "which", "that", "this",
                     "with", "have", "your", "would", "could", "tell",
                     "about", "describe", "explain", "give", "make",
                     "from", "they", "them", "been", "were", "will"}
        q_words -= stopwords

        answer_words = set(re.findall(r'\b[a-z]{4,}\b', answer_lower))

        # Count strong keyword matches
        strong_hits = sum(1 for kw in strong_keywords if kw in answer_lower)
        strong_score = min(strong_hits / max(len(strong_keywords) * 0.3, 1), 1.0) * 60

        # Count question-topic matches
        topic_hits = len(q_words & answer_words)
        topic_score = min(topic_hits / max(len(q_words) * 0.4, 1), 1.0) * 40

        raw = strong_score + topic_score
        return min(max(raw, 5), 100)

    # ==========================================
    # VOCABULARY RICHNESS
    # ==========================================
    def _vocab_score(self, answer: str) -> float:
        """
        Rewards using a variety of words (not repeating the same words).
        """
        words = re.findall(r'\b[a-z]{3,}\b', answer.lower())
        if not words:
            return 0
        unique_ratio = len(set(words)) / len(words)
        # Scale: 0.5 ratio → 50 pts, 0.8+ ratio → 100 pts
        score = min(unique_ratio * 125, 100)
        return round(score, 2)

    # ==========================================
    # ENGLISH DETECTION
    # ==========================================
    def _is_english(self, text: str) -> bool:
        """
        Basic English detection:
        - Checks that most words are in English character set
        - Checks for common English function words
        - Rejects if text has too many non-ASCII characters
        """
        # Must have mostly ASCII letters
        ascii_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return False
        if ascii_chars / total_alpha < 0.85:
            return False

        # Check for at least some common English words
        common_english = {
            "i", "the", "a", "an", "is", "are", "was", "were",
            "my", "me", "we", "it", "in", "on", "at", "to",
            "and", "or", "but", "not", "have", "has", "had",
            "be", "been", "do", "did", "will", "would", "can",
            "could", "should", "may", "might", "for", "of",
            "with", "from", "this", "that", "am", "he", "she",
            "they", "you", "your", "our", "their", "its"
        }

        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        english_hits = len(words & common_english)

        # If answer has 15+ words but no common English words at all, suspicious
        word_count = len(text.split())
        if word_count >= 10 and english_hits == 0:
            return False

        return True

    # ==========================================
    # DIMENSION AVERAGING
    # ==========================================
    def _dimension_score(self, answer_scores: List[Dict], key: str) -> float:
        vals = [s[key] for s in answer_scores if key in s]
        if not vals:
            return 0
        return sum(vals) / len(vals)

    # ==========================================
    # FEEDBACK GENERATION
    # ==========================================
    def _generate_feedback(
        self,
        overall: float,
        rejection_flags: List[str],
        answer_scores: List[Dict]
    ) -> str:
        parts = []

        # Rejection warnings
        short_count = sum(1 for s in answer_scores if s.get("reason") == "too_short")
        non_eng_count = sum(1 for s in answer_scores if s.get("reason") == "non_english")
        empty_count = sum(1 for s in answer_scores if s.get("reason") == "empty")

        if non_eng_count > 0:
            parts.append(
                f"{non_eng_count} answer(s) were detected as non-English and received very low scores. "
                "Please answer all questions in English."
            )

        if short_count > 0:
            parts.append(
                f"{short_count} answer(s) were too short (less than 15 words). "
                "Interviewers expect detailed, well-explained responses."
            )

        if empty_count > 0:
            parts.append(f"{empty_count} question(s) were left unanswered.")

        # Performance feedback based on score
        if overall >= 85:
            parts.append(
                "Excellent performance! Your answers were detailed, relevant, and well-structured. "
                "You demonstrated strong communication and technical knowledge."
            )
        elif overall >= 70:
            parts.append(
                "Good performance overall. Your answers showed solid understanding. "
                "Try to include more specific examples and elaborate further on technical details."
            )
        elif overall >= 55:
            parts.append(
                "Average performance. Some answers lacked depth or relevance. "
                "Focus on providing concrete examples and expanding your responses."
            )
        elif overall >= 35:
            parts.append(
                "Below average. Many answers were too brief or lacked relevant content. "
                "Practice giving detailed, structured answers using the STAR method "
                "(Situation, Task, Action, Result)."
            )
        else:
            parts.append(
                "Needs significant improvement. Most answers were too short, off-topic, or not in English. "
                "Study the role requirements, practice answering in English, and aim for at least "
                "50-100 words per answer."
            )

        return " ".join(parts)


# IMPORTANT: create instance
ai_model = AIModel()