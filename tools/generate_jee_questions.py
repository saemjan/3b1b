#!/usr/bin/env python3
"""Generate JEE Advanced-style questions from concept graph"""
import json
import random
from pathlib import Path
from typing import List, Dict

class JEEQuestionGenerator:
    def __init__(self):
        self.concept_graph = json.loads(
            Path("knowledge_base/jee_patterns.json").read_text()
        )["concept_graph"]
    
    def generate_mechanics_question(self) -> Dict:
        """Generate mechanics question (JEE style)"""
        question_types = [
            {
                "type": "integer",
                "template": "A block of mass {m} kg starts from rest on a frictionless surface. "
                           "A force of {F} N is applied for {t} s. The final velocity is ___ m/s.",
                "generate": lambda: {
                    "m": random.randint(1, 10),
                    "F": random.randint(10, 100),
                    "t": random.randint(2, 10),
                },
                "solve": lambda params: round(params["F"] * params["t"] / params["m"], 2)
            },
            {
                "type": "mcq",
                "template": "Two identical discs roll without slipping. If disc A has velocity v₁ "
                           "and disc B has velocity v₂, and they reach the same height, then:",
                "options": [
                    "v₁ = v₂",
                    "v₁ > v₂",
                    "v₁ < v₂",
                    "Cannot be determined"
                ],
                "correct": 0
            }
        ]
        
        q_type = random.choice(question_types)
        
        if q_type["type"] == "integer":
            params = q_type["generate"]()
            question_text = q_type["template"].format(**params)
            answer = q_type["solve"](params)
            
            return {
                "question_text": question_text,
                "question_type": "integer",
                "answer": int(answer) if answer == int(answer) else round(answer, 2),
                "options": [],
                "correct_answer": str(int(answer)) if answer == int(answer) else str(round(answer, 2)),
                "concepts": ["newton_laws", "kinematics"]
            }
        else:
            return {
                "question_text": q_type["template"],
                "question_type": "mcq",
                "options": q_type["options"],
                "correct_answer": chr(65 + q_type["correct"]),  # A, B, C, D
                "concepts": ["rotation", "energy"]
            }
    
    def generate_batch(self, n: int = 10) -> List[Dict]:
        """Generate batch of JEE questions"""
        questions = []
        for i in range(n):
            q = self.generate_mechanics_question()
            q["video_id"] = f"jee_mech_{i+1:03d}"
            questions.append(q)
        return questions

def main():
    generator = JEEQuestionGenerator()
    questions = generator.generate_batch(10)
    
    # Save as CSV
    import csv
    with open("content/jee_questions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "video_id", "question_text", "question_type", 
            "options", "correct_answer", "concepts"
        ])
        writer.writeheader()
        writer.writerows(questions)
    
    print(f"✓ Generated {len(questions)} JEE questions")

if __name__ == "__main__":
    main()
