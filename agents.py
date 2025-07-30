from crewai import Agent
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

class FormIntakeAgent(Agent):
    def run(self, **kwargs):
        print("FormIntakeAgent: Collecting candidate info...")
        return {"name": "Test User", "email": "test@example.com"}

class SkillMatcherAgent(Agent):
    def run(self, **kwargs):
        print("SkillMatcherAgent: Matching skills...")
        return {"skills_matched": True}

class CodingTestAgent(Agent):
    def run(self, **kwargs):
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = "Generate a unique easy-level Python coding question for interviews."
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        question = response.choices[0].message.content.strip()
        print("Generated Coding Question:", question)
        candidate_answer = kwargs.get("candidate_answer", "def add(a, b): return a + b")
        eval_prompt = f"Here is a coding question:\n{question}\n\nHere is the candidate's answer:\n{candidate_answer}\n\nIs the answer correct? Reply with 'Yes' or 'No' and a brief explanation."
        eval_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}]
        )
        evaluation = eval_response.choices[0].message.content.strip()
        print("Evaluation:", evaluation)
        return {"question": question, "evaluation": evaluation}

class TechInterviewAgent(Agent):
    def run(self, **kwargs):
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = "Generate a unique technical interview question for a Python developer."
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        question = response.choices[0].message.content.strip()
        print("Generated Technical Interview Question:", question)
        candidate_answer = kwargs.get("candidate_answer", "You can use a for loop to iterate through the list and keep track of the largest number.")
        eval_prompt = f"Here is a technical interview question:\n{question}\n\nHere is the candidate's answer:\n{candidate_answer}\n\nIs the answer correct? Reply with 'Yes' or 'No' and a brief explanation."
        eval_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}]
        )
        evaluation = eval_response.choices[0].message.content.strip()
        print("Evaluation:", evaluation)
        return {"question": question, "evaluation": evaluation}

class HRInterviewAgent(Agent):
    def run(self, **kwargs):
        print("HRInterviewAgent: Conducting HR interview...")
        return {"hr_interview_passed": True}

class OfferLetterAgent(Agent):
    def run(self, **kwargs):
        print("OfferLetterAgent: Sending offer letter...")
        return {"offer_sent": True}

class RejectionAgent(Agent):
    def run(self, **kwargs):
        print("RejectionAgent: Sending rejection email...")
        return {"rejection_sent": True} 