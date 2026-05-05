# src/modules/ai_model.py
"""
CareerReady AI — Interview Answer Analyzer
=========================================
Scoring is based on:
  1. RELEVANCE  (50%) — Does the answer actually address the question?
  2. SPECIFICITY(25%) — Does it use concrete examples, facts, role-specific terms?
  3. QUALITY    (15%) — Grammar, vocabulary, coherence (not raw length)
  4. COMPLETENESS(10%)— Does it cover the key components the question expects?

Length is a secondary signal, NOT the primary driver.
A short but highly relevant answer beats a long but off-topic one.
"""

import re
import json
from typing import List, Dict, Any


# ─────────────────────────────────────────────
# QUESTION-CATEGORY KEYWORD MAP
# Used to match question intent → expected answer keywords
# ─────────────────────────────────────────────
QUESTION_INTENTS = {
    # Behavioral
    "tell me about yourself": {
        "category": "behavioral",
        "expected_keywords": ["experience", "background", "work", "studied", "years", "skills", "career", "graduated", "role", "position", "currently", "previously"],
        "avoid": ["i don't know", "not sure", "nothing"]
    },
    "strength": {
        "category": "behavioral",
        "expected_keywords": ["strength", "skill", "good at", "excel", "strength is", "ability", "confident", "capable", "example", "situation", "result"]
    },
    "weakness": {
        "category": "behavioral",
        "expected_keywords": ["weakness", "working on", "improve", "challenge", "sometimes", "learning", "developing", "aware", "better"]
    },
    "why do you want": {
        "category": "motivation",
        "expected_keywords": ["passion", "interest", "goal", "opportunity", "career", "growth", "company", "role", "contribute", "excited", "motivated"]
    },
    "handle pressure": {
        "category": "behavioral",
        "expected_keywords": ["pressure", "deadline", "stress", "calm", "prioritize", "organize", "example", "situation", "focused", "manage", "delivered"]
    },
    "challenge": {
        "category": "behavioral",
        "expected_keywords": ["challenge", "difficult", "problem", "situation", "solved", "overcame", "result", "learned", "team", "approach", "action"]
    },
    "teamwork": {
        "category": "behavioral",
        "expected_keywords": ["team", "collaborate", "together", "members", "project", "role", "communication", "contributed", "support", "goal", "achieved"]
    },
    "leadership": {
        "category": "behavioral",
        "expected_keywords": ["lead", "team", "managed", "directed", "goal", "motivated", "decision", "responsibility", "outcome", "guided"]
    },
    "conflict": {
        "category": "behavioral",
        "expected_keywords": ["conflict", "disagreement", "resolved", "communicate", "listen", "understand", "compromise", "solution", "approach", "professional"]
    },
    "5 years": {
        "category": "motivation",
        "expected_keywords": ["goal", "career", "grow", "senior", "lead", "specialize", "opportunity", "contribute", "develop", "position"]
    },
    "why should we hire": {
        "category": "motivation",
        "expected_keywords": ["skill", "experience", "contribute", "value", "unique", "able", "qualified", "passion", "dedicated", "result", "achieve"]
    },
    "manage time": {
        "category": "behavioral",
        "expected_keywords": ["time", "prioritize", "schedule", "plan", "organize", "deadline", "task", "manage", "list", "focus", "complete"]
    },

    # Technical — Software
    "programming": {
        "category": "technical",
        "expected_keywords": ["python", "java", "javascript", "c++", "language", "code", "program", "develop", "framework", "library", "experience", "project"]
    },
    "debug": {
        "category": "technical",
        "expected_keywords": ["debug", "error", "log", "test", "step", "breakpoint", "trace", "fix", "identify", "issue", "console", "reproduce"]
    },
    "api": {
        "category": "technical",
        "expected_keywords": ["api", "endpoint", "request", "response", "rest", "http", "json", "data", "server", "client", "call", "integrate"]
    },
    "database": {
        "category": "technical",
        "expected_keywords": ["database", "sql", "query", "table", "record", "postgresql", "mysql", "mongodb", "data", "schema", "normalize", "index"]
    },
    "object-oriented": {
        "category": "technical",
        "expected_keywords": ["class", "object", "inheritance", "encapsulation", "polymorphism", "abstraction", "method", "instance", "attribute", "oop"]
    },
    "git": {
        "category": "technical",
        "expected_keywords": ["git", "commit", "push", "pull", "branch", "merge", "version", "repository", "conflict", "remote", "clone", "track"]
    },

    # Nursing / Healthcare
    "patient": {
        "category": "clinical",
        "expected_keywords": ["patient", "care", "assess", "monitor", "medication", "nurse", "doctor", "report", "comfort", "family", "safety", "record"]
    },
    "emergency": {
        "category": "clinical",
        "expected_keywords": ["emergency", "immediate", "assess", "vital", "call", "doctor", "priority", "action", "stabilize", "protocol", "calm", "report"]
    },
    "medication": {
        "category": "clinical",
        "expected_keywords": ["medication", "dosage", "administer", "prescription", "check", "verify", "patient", "safety", "allergies", "route", "record"]
    },
    "infection": {
        "category": "clinical",
        "expected_keywords": ["infection", "hygiene", "handwashing", "ppe", "sterilize", "protocol", "prevent", "isolate", "clean", "disinfect", "gloves"]
    },

    # Teaching
    "student": {
        "category": "teaching",
        "expected_keywords": ["student", "learn", "understand", "engage", "teach", "method", "activity", "progress", "assess", "support", "classroom"]
    },
    "lesson plan": {
        "category": "teaching",
        "expected_keywords": ["lesson", "plan", "objective", "activity", "material", "assess", "topic", "grade", "standard", "engage", "outcome"]
    },
    "classroom management": {
        "category": "teaching",
        "expected_keywords": ["classroom", "manage", "discipline", "rule", "behavior", "student", "engage", "routine", "expectation", "positive", "consequence"]
    },

    # Civil Engineering
    "structural": {
        "category": "engineering",
        "expected_keywords": ["structure", "load", "beam", "column", "material", "design", "stress", "concrete", "steel", "foundation", "analysis", "engineer"]
    },
    "blueprint": {
        "category": "engineering",
        "expected_keywords": ["blueprint", "drawing", "plan", "read", "dimension", "scale", "specification", "symbol", "structure", "site", "design"]
    },
    "project cost": {
        "category": "engineering",
        "expected_keywords": ["cost", "estimate", "budget", "material", "labor", "quantity", "survey", "scope", "calculate", "project", "expense"]
    },
    "site safety": {
        "category": "engineering",
        "expected_keywords": ["safety", "ppe", "inspection", "hazard", "protocol", "training", "equipment", "regulation", "risk", "compliance", "worker"]
    },

    # General fallback
    "motivate": {
        "category": "behavioral",
        "expected_keywords": ["motivate", "passion", "drive", "goal", "achieve", "inspire", "reward", "purpose", "grow", "result", "challenge"]
    },
    "achievement": {
        "category": "behavioral",
        "expected_keywords": ["achieve", "accomplish", "result", "success", "proud", "impact", "outcome", "project", "team", "recognition", "goal"]
    }
}

# General strong keywords that count across all question types
GENERAL_POSITIVE_WORDS = [
    "example", "specifically", "for instance", "in my experience",
    "i worked", "i managed", "i developed", "i led", "i created",
    "result was", "outcome was", "we achieved", "successfully",
    "i learned", "i improved", "i contributed", "responsible for",
    "situation was", "my role", "i coordinated", "i implemented"
]

# Filler / low-quality phrases
FILLER_PHRASES = [
    "i think i am", "i believe i can", "i am a person who",
    "in conclusion", "to summarize", "as i said", "basically",
    "and stuff", "and things", "et cetera", "blah blah",
    "i don't really", "i'm not sure but", "maybe", "i guess",
    "kind of", "sort of", "you know", "like i said"
]

STOPWORDS = {
    "what", "when", "where", "which", "that", "this", "with", "have",
    "your", "would", "could", "tell", "about", "describe", "explain",
    "give", "make", "from", "they", "them", "been", "were", "will",
    "should", "does", "into", "some", "very", "also", "just", "over",
    "then", "than", "more", "such", "each", "both", "here", "there"
}

COMMON_ENGLISH = {
    "i", "the", "a", "an", "is", "are", "was", "were", "my", "me",
    "we", "it", "in", "on", "at", "to", "and", "or", "but", "not",
    "have", "has", "had", "be", "been", "do", "did", "will", "would",
    "can", "could", "should", "may", "might", "for", "of", "with",
    "from", "this", "that", "am", "he", "she", "they", "you", "your",
    "our", "their", "its", "so", "if", "as", "up", "by", "how"
}


class AIModel:
    def __init__(self):
        print("CareerReady AI Model initialized — Relevance-first scoring active")

    # ══════════════════════════════════════════════
    # MAIN ENTRY: Analyze all answers
    # ══════════════════════════════════════════════
    def analyze_interview_answers(self, data: List[Dict[str, str]]) -> Dict[str, Any]:
        if not data:
            return self._empty_result("No answers provided.")

        scored = []
        for item in data:
            question = (item.get("question") or "").strip()
            answer   = (item.get("answer")   or "").strip()
            scored.append(self._score_answer(question, answer))

        overall         = round(self._safe_avg([s["score"]          for s in scored]), 2)
        communication   = round(self._safe_avg([s["communication"]  for s in scored]), 2)
        technical       = round(self._safe_avg([s["technical"]      for s in scored]), 2)
        problem_solving = round(self._safe_avg([s["problem_solving"]for s in scored]), 2)
        confidence      = round(self._safe_avg([s["confidence"]     for s in scored]), 2)
        feedback        = self._generate_feedback(overall, scored)

        return {
            "score":           overall,
            "feedback":        feedback,
            "communication":   communication,
            "technical":       technical,
            "problem_solving": problem_solving,
            "confidence":      confidence
        }

    # ══════════════════════════════════════════════
    # SCORE A SINGLE ANSWER
    # ══════════════════════════════════════════════
    def _score_answer(self, question: str, answer: str) -> Dict:
        base = {
            "question":       question,
            "score":          0,
            "communication":  0,
            "technical":      0,
            "problem_solving":0,
            "confidence":     0,
            "issues":         []
        }

        # ── Empty answer ──
        if not answer:
            base["issues"].append("empty")
            return base

        # ── English check ──
        if not self._is_english(answer):
            base["score"]          = 5
            base["communication"]  = 5
            base["technical"]      = 5
            base["problem_solving"]= 5
            base["confidence"]     = 5
            base["issues"].append("non_english")
            return base

        word_count = len(answer.split())

        # ── Minimum viable answer: 8 words ──
        if word_count < 8:
            partial = max(5, word_count * 3)
            base["score"]          = partial
            base["communication"]  = partial
            base["technical"]      = partial
            base["problem_solving"]= partial
            base["confidence"]     = partial
            base["issues"].append("too_short")
            return base

        # ────────────────────────────────────────
        # Core scoring components
        # ────────────────────────────────────────

        # 1. RELEVANCE (50%) — does the answer address this question?
        relevance = self._relevance_score(question, answer)

        # 2. SPECIFICITY (25%) — concrete examples, role terms, personal experience
        specificity = self._specificity_score(answer)

        # 3. QUALITY (15%) — vocabulary diversity, sentence coherence, no fillers
        quality = self._quality_score(answer)

        # 4. COMPLETENESS (10%) — covers key components the question expects
        completeness = self._completeness_score(question, answer, word_count)

        # ── Weighted composite ──
        raw = (relevance * 0.50) + (specificity * 0.25) + (quality * 0.15) + (completeness * 0.10)
        score = round(min(max(raw, 5), 100), 2)

        # ── Dimension breakdown ──
        q_cat = self._detect_category(question)

        comm  = round(min((quality * 0.5 + completeness * 0.3 + relevance * 0.2), 100), 2)
        tech  = round(min((relevance * 0.6 + specificity * 0.4) if q_cat == "technical" else (relevance * 0.4 + specificity * 0.6), 100), 2)
        prob  = round(min((relevance * 0.45 + specificity * 0.35 + completeness * 0.20), 100), 2)
        conf  = round(min((quality * 0.4 + completeness * 0.35 + score * 0.25), 100), 2)

        base.update({
            "score":           score,
            "communication":   comm,
            "technical":       tech,
            "problem_solving": prob,
            "confidence":      conf,
            "relevance":       relevance,
            "specificity":     specificity,
            "quality":         quality,
            "completeness":    completeness
        })
        return base

    # ══════════════════════════════════════════════
    # 1. RELEVANCE: Does the answer match the question's intent?
    # ══════════════════════════════════════════════
    def _relevance_score(self, question: str, answer: str) -> float:
        q_lower = question.lower()
        a_lower = answer.lower()

        # Find matching intent
        intent_data = None
        best_match_len = 0
        for trigger, data in QUESTION_INTENTS.items():
            if trigger in q_lower and len(trigger) > best_match_len:
                intent_data = data
                best_match_len = len(trigger)

        if intent_data:
            expected = intent_data.get("expected_keywords", [])
            avoid    = intent_data.get("avoid", [])

            # Penalty for avoid phrases
            avoid_hits = sum(1 for phrase in avoid if phrase in a_lower)
            if avoid_hits > 0:
                return max(10.0, 30.0 - (avoid_hits * 10))

            # Score based on expected keyword coverage
            hits = sum(1 for kw in expected if kw in a_lower)
            coverage = hits / max(len(expected), 1)

            # Partial credit for near-miss (word overlap)
            q_words = set(re.findall(r'\b[a-z]{4,}\b', q_lower)) - STOPWORDS
            a_words = set(re.findall(r'\b[a-z]{4,}\b', a_lower)) - STOPWORDS
            overlap_ratio = len(q_words & a_words) / max(len(q_words), 1)

            relevance = (coverage * 70) + (overlap_ratio * 30)

        else:
            # Generic fallback: question word overlap + general positive words
            q_words = set(re.findall(r'\b[a-z]{4,}\b', q_lower)) - STOPWORDS
            a_words = set(re.findall(r'\b[a-z]{4,}\b', a_lower)) - STOPWORDS
            overlap_ratio = len(q_words & a_words) / max(len(q_words), 1)

            general_hits = sum(1 for phrase in GENERAL_POSITIVE_WORDS if phrase in a_lower)
            general_score = min(general_hits / 3, 1.0) * 40

            relevance = (overlap_ratio * 60) + general_score

        return round(min(max(relevance, 5), 100), 2)

    # ══════════════════════════════════════════════
    # 2. SPECIFICITY: Concrete examples, personal experience, role terms
    # ══════════════════════════════════════════════
    def _specificity_score(self, answer: str) -> float:
        a_lower = answer.lower()

        # Phrases that signal specificity
        specific_signals = [
            "for example", "for instance", "specifically", "in my experience",
            "i worked on", "i developed", "i managed", "i led", "i created",
            "i was responsible", "in one case", "one time", "at my previous",
            "during my", "in my previous", "i used", "i implemented",
            "the result was", "this helped", "we achieved", "i contributed",
            "when i was", "i noticed", "i realized", "i decided"
        ]

        hits = sum(1 for s in specific_signals if s in a_lower)
        signal_score = min(hits / 3, 1.0) * 60

        # Numbers / metrics (years, percentages, quantities)
        has_numbers = bool(re.search(r'\b\d+\b', answer))
        number_bonus = 15 if has_numbers else 0

        # Named tools / proper nouns (capitalized mid-sentence)
        proper_nouns = re.findall(r'(?<![.!?] )\b[A-Z][a-z]{2,}\b', answer)
        proper_bonus = min(len(proper_nouns) * 5, 25)

        total = signal_score + number_bonus + proper_bonus
        return round(min(max(total, 5), 100), 2)

    # ══════════════════════════════════════════════
    # 3. QUALITY: Vocabulary, coherence, no fillers
    # ══════════════════════════════════════════════
    def _quality_score(self, answer: str) -> float:
        a_lower = answer.lower()
        words   = re.findall(r'\b[a-z]{3,}\b', a_lower)

        if not words:
            return 0

        # Vocabulary diversity
        unique_ratio = len(set(words)) / len(words)
        vocab_score  = min(unique_ratio * 120, 70)

        # Filler penalty
        filler_count = sum(1 for f in FILLER_PHRASES if f in a_lower)
        filler_penalty = min(filler_count * 8, 30)

        # Sentence structure bonus (uses punctuation properly)
        sentences = re.split(r'[.!?]+', answer.strip())
        valid_sentences = [s.strip() for s in sentences if len(s.strip().split()) >= 3]
        structure_bonus = min(len(valid_sentences) * 5, 30)

        total = vocab_score + structure_bonus - filler_penalty
        return round(min(max(total, 5), 100), 2)

    # ══════════════════════════════════════════════
    # 4. COMPLETENESS: Does the answer cover expected components?
    # ══════════════════════════════════════════════
    def _completeness_score(self, question: str, answer: str, word_count: int) -> float:
        # Word count contributes but is capped — quality > quantity
        if word_count < 15:
            length_score = 30
        elif word_count < 30:
            length_score = 50
        elif word_count < 60:
            length_score = 70
        elif word_count < 100:
            length_score = 85
        else:
            length_score = 95

        # Check if it answers WHO/WHAT/WHEN/HOW/WHY if question has them
        q_lower = question.lower()
        a_lower = answer.lower()

        completeness_boost = 0
        if "how" in q_lower and any(w in a_lower for w in ["by", "through", "using", "method", "approach", "step", "process"]):
            completeness_boost += 10
        if "why" in q_lower and any(w in a_lower for w in ["because", "reason", "since", "therefore", "due to", "motivated"]):
            completeness_boost += 10
        if "what" in q_lower and any(w in a_lower for w in ["is", "are", "was", "involves", "means", "refers"]):
            completeness_boost += 5
        if "describe" in q_lower and word_count >= 30:
            completeness_boost += 10

        total = min(length_score + completeness_boost, 100)
        return round(max(total, 5), 2)

    # ══════════════════════════════════════════════
    # DETECT QUESTION CATEGORY
    # ══════════════════════════════════════════════
    def _detect_category(self, question: str) -> str:
        q_lower = question.lower()
        for trigger, data in QUESTION_INTENTS.items():
            if trigger in q_lower:
                return data.get("category", "general")
        return "general"

    # ══════════════════════════════════════════════
    # ENGLISH DETECTION
    # ══════════════════════════════════════════════
    def _is_english(self, text: str) -> bool:
        ascii_chars  = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        total_alpha  = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return False
        if ascii_chars / total_alpha < 0.85:
            return False
        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        english_hits = len(words & COMMON_ENGLISH)
        if len(text.split()) >= 8 and english_hits == 0:
            return False
        return True

    # ══════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════
    def _safe_avg(self, values: List[float]) -> float:
        vals = [v for v in values if v is not None]
        return sum(vals) / len(vals) if vals else 0

    def _empty_result(self, msg: str) -> Dict:
        return {
            "score": 0, "feedback": msg,
            "communication": 0, "technical": 0,
            "problem_solving": 0, "confidence": 0
        }

    # ══════════════════════════════════════════════
    # FEEDBACK GENERATION
    # ══════════════════════════════════════════════
    def _generate_feedback(self, overall: float, scored: List[Dict]) -> str:
        parts = []

        non_eng = sum(1 for s in scored if "non_english" in s.get("issues", []))
        empty   = sum(1 for s in scored if "empty"       in s.get("issues", []))
        too_short = sum(1 for s in scored if "too_short"  in s.get("issues", []))

        if non_eng:
            parts.append(
                f"{non_eng} answer(s) were detected as non-English and received very low scores. "
                "Please answer all questions in English."
            )
        if empty:
            parts.append(f"{empty} question(s) were left unanswered.")
        if too_short:
            parts.append(
                f"{too_short} answer(s) were too brief (fewer than 8 words). "
                "Provide complete, thoughtful responses."
            )

        # Identify weakest dimension
        avg_rel = self._safe_avg([s.get("relevance", 0)    for s in scored])
        avg_spc = self._safe_avg([s.get("specificity", 0)  for s in scored])
        avg_qly = self._safe_avg([s.get("quality", 0)      for s in scored])

        if avg_rel < 45:
            parts.append(
                "Many answers did not directly address the question asked. "
                "Read each question carefully and answer it specifically — don't give a generic response."
            )
        elif avg_spc < 40:
            parts.append(
                "Your answers lacked specific examples and evidence. "
                "Use real situations from your experience (or study) to support your answers."
            )

        # Overall verdict
        if overall >= 85:
            parts.append(
                "Excellent overall performance! Your answers were highly relevant, specific, and well-structured. "
                "You demonstrate strong readiness for a face-to-face interview."
            )
        elif overall >= 70:
            parts.append(
                "Good performance. Your answers show solid understanding. "
                "To reach the next level, add more specific examples and directly address each question's core ask."
            )
        elif overall >= 55:
            parts.append(
                "Average performance. Some answers lacked direct relevance to the question. "
                "Practice answering each question specifically — relevance matters more than length."
            )
        elif overall >= 35:
            parts.append(
                "Below average. Focus on reading each question carefully and responding directly to what is being asked. "
                "Use the STAR method: Situation → Task → Action → Result."
            )
        else:
            parts.append(
                "Significant improvement needed. Most answers were off-topic, too short, or not in English. "
                "Study your target role and practice giving focused, English answers that directly address each question."
            )

        return " ".join(parts)


# Module-level instance
ai_model = AIModel()