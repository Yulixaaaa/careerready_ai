import random
from typing import List, Dict, Any

class AIModel:
    def __init__(self):
        print("AI Model initialized (mock mode)")

    def analyze_interview_answers(self, data: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Mock AI analysis function
        """
        score = random.uniform(50, 95)

        return {
            "score": score,
            "feedback": "Mock AI analysis completed successfully."
        }

# IMPORTANT: create instance
ai_model = AIModel()