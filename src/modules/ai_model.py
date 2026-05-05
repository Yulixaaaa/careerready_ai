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

    def _score_single_answer(self, question: str, answer: str) -> Dict:
        base = {"score": 0, "rejected": False, "reason": "",
                "communication": 0, "technical": 0, "problem_solving": 0, "confidence": 0}

        if not answer:
            base.update({"rejected": True, "reason": "empty"})
            return base

        word_count = len(answer.split())

        if word_count < 10:
            s = max(3, word_count * 3)
            base.update({"score": s, "rejected": True, "reason": "too_short",
                         "communication": s, "technical": s, "problem_solving": s, "confidence": s})
            return base

        if not self._is_english(answer):
            base.update({"score": 5, "rejected": True, "reason": "non_english",
                         "communication": 5, "technical": 5, "problem_solving": 5, "confidence": 5})
            return base

        # RELEVANCE is the primary driver (50%)
        relevance_score = self._relevance_score(question, answer)
        substance_score = self._substance_score(answer)
        coherence_score = self._coherence_score(answer)
        length_bonus    = min(self._length_bonus(word_count), 15)

        raw   = (relevance_score * 0.50) + (substance_score * 0.30) + (coherence_score * 0.15) + length_bonus
        score = round(min(max(raw, 3), 100), 2)

        comm  = round(min(coherence_score * 0.6 + relevance_score * 0.4, 100), 2)
        tech  = round(min(relevance_score * 0.7 + substance_score * 0.3, 100), 2)
        prob  = round(min(substance_score * 0.6 + relevance_score * 0.4, 100), 2)
        conf  = round(min(coherence_score * 0.5 + score * 0.5, 100), 2)

        base.update({"score": score, "reason": "ok",
                     "communication": comm, "technical": tech,
                     "problem_solving": prob, "confidence": conf})
        return base

    def _relevance_score(self, question: str, answer: str) -> float:
        """Score how directly the answer addresses the question."""
        q_lower = question.lower()
        a_lower = answer.lower()

        stopwords = {
            "what","when","where","which","that","this","with","have","your",
            "would","could","tell","about","describe","explain","give","make",
            "from","they","them","been","were","will","does","some","most",
            "many","more","very","much","each","example","please","share","discuss"
        }
        q_words    = set(re.findall(r'\b[a-z]{4,}\b', q_lower)) - stopwords
        a_words    = set(re.findall(r'\b[a-z]{4,}\b', a_lower))
        topic_hits = len(q_words & a_words)
        topic_score = min(topic_hits / max(len(q_words) * 0.4, 1), 1.0) * 50

        # Signal groups — each group counts once to avoid keyword stuffing
        signal_groups = {
            "experience":  ["experience","worked","years","background","previously","career"],
            "example":     ["example","instance","situation","case","once","time","when"],
            "action":      ["managed","developed","created","implemented","handled","solved",
                            "built","led","improved","designed","achieved","completed"],
            "result":      ["result","outcome","impact","success","increased","reduced",
                            "saved","delivered","accomplished"],
            "reasoning":   ["because","therefore","since","reason","believe","think",
                            "understand","learned","realized","approach","strategy"],
            "specificity": ["specific","particular","especially","detail","process",
                            "method","technique","tool","system","procedure"],
        }
        groups_hit = sum(1 for gw in signal_groups.values() if any(w in a_lower for w in gw))
        signal_score = (groups_hit / len(signal_groups)) * 50

        return min(max(topic_score + signal_score, 3), 100)

    def _substance_score(self, answer: str) -> float:
        """Depth of content: numbers, reasoning, actions, STAR structure."""
        a_lower = answer.lower()
        numbers_n   = len(re.findall(r'\b\d+\b', a_lower))
        reasoning_n = len(re.findall(
            r'\b(because|therefore|since|as a result|which led|this helped|'
            r'in order to|due to|consequently|so that|enabled|allowed)\b', a_lower))
        actions_n = len(re.findall(
            r'\b(managed|built|created|developed|implemented|resolved|improved|'
            r'designed|analyzed|communicated|collaborated|handled|led|established|'
            r'organized|coordinated|achieved|delivered|maintained|ensured)\b', a_lower))
        structure_n = len(re.findall(
            r'\b(situation|task|action|result|challenge|approach|outcome|'
            r'goal|objective|response|decision|solution)\b', a_lower))

        raw = (min(numbers_n/3, 1.0) * 25 + min(reasoning_n/2, 1.0) * 30 +
               min(actions_n/3, 1.0) * 25  + min(structure_n/3, 1.0) * 20)
        return min(max(raw, 5), 100)

    def _coherence_score(self, answer: str) -> float:
        """Clarity and fluency: sentence length, vocabulary diversity."""
        sentences = [s.strip() for s in re.split(r'[.!?]+', answer.strip()) if len(s.strip()) > 5]
        if not sentences:
            return 10

        avg_wps = sum(len(s.split()) for s in sentences) / len(sentences)
        if 8 <= avg_wps <= 22:   wps_score = 100
        elif avg_wps < 8:         wps_score = avg_wps / 8 * 100
        else:                     wps_score = max(60, 100 - (avg_wps - 22) * 3)

        words = re.findall(r'\b[a-z]{3,}\b', answer.lower())
        vocab_score    = min(len(set(words)) / max(len(words), 1) * 130, 100) if words else 10
        sentence_score = min(len(sentences) / 3 * 100, 100)

        return round(wps_score * 0.4 + vocab_score * 0.4 + sentence_score * 0.2, 2)

    def _length_bonus(self, wc: int) -> float:
        """Tiny bonus for length — max 15 pts so long irrelevant answers don't game the score."""
        if wc < 10:  return 0
        if wc < 20:  return 3
        if wc < 40:  return 6
        if wc < 70:  return 9
        if wc < 120: return 12
        return 15

    def _is_english(self, text: str) -> bool:
        ascii_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0 or ascii_chars / total_alpha < 0.85:
            return False
        common_en = {
            "i","the","a","an","is","are","was","were","my","me","we","it",
            "in","on","at","to","and","or","but","not","have","has","had",
            "be","been","do","did","will","would","can","could","should",
            "may","might","for","of","with","from","this","that","am",
            "he","she","they","you","your","our","their","its"
        }
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
            parts.append(f"{non_eng} answer(s) were not in English and received very low scores. All answers must be in English.")
        if short:
            parts.append(f"{short} answer(s) were too short. Aim for at least 10 words with clear, specific content.")
        if empty:
            parts.append(f"{empty} question(s) were left blank.")

        if overall >= 85:
            parts.append("Excellent performance! Your answers were relevant, specific, and well-structured. You clearly understand the role and demonstrated strong real-world examples.")
        elif overall >= 70:
            parts.append("Good performance. Your answers were largely on-topic and showed solid understanding. To score higher, include more concrete examples and specific results.")
        elif overall >= 55:
            parts.append("Average performance. Some answers lacked direct relevance to the questions asked. Focus on answering exactly what was asked — use the STAR method: Situation, Task, Action, Result.")
        elif overall >= 35:
            parts.append("Below average. Your answers were often off-topic or lacked substance. Read each question carefully and answer it directly with specific examples.")
        else:
            parts.append("Needs significant improvement. Answers appear generic, off-topic, or too short. Study the job role and answer each question directly and specifically.")

        return " ".join(parts)


ai_model = AIModel()