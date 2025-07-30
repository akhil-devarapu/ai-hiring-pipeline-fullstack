import yaml
import importlib
import logging
import sys
from dotenv import load_dotenv
load_dotenv()
from crewai import Crew
from agents import (
    FormIntakeAgent, SkillMatcherAgent, CodingTestAgent,
    TechInterviewAgent, HRInterviewAgent, OfferLetterAgent, RejectionAgent
)
from tasks import (
    form_intake_task, skill_match_task, coding_test_task,
    tech_interview_task, hr_interview_task, offer_letter_task, rejection_task
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_crew_config(path='crew.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def dynamic_import(module_path, class_name):
    module = importlib.import_module(module_path)
    return getattr(module, class_name)

def prompt_candidate_info():
    print("\n--- Candidate Form Intake ---")
    name = input("Candidate Name: ")
    email = input("Email: ")
    phone = input("Phone: ")
    role = input("Role Applied For (SDI/SDM): ")
    skills = input("Skills (comma-separated): ")
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "role": role,
        "skills": [s.strip() for s in skills.split(",") if s.strip()]
    }

def main():
    # Instantiate agents with required fields
    form_agent = FormIntakeAgent(
        role="Form Intake",
        goal="Collect candidate information and resume.",
        backstory="You are responsible for collecting all necessary candidate details at the start of the hiring process."
    )
    skill_agent = SkillMatcherAgent(
        role="Skill Matcher",
        goal="Check if candidate skills match the job requirements.",
        backstory="You ensure only qualified candidates proceed."
    )
    code_agent = CodingTestAgent(
        role="Coding Test",
        goal="Send and grade coding assessments.",
        backstory="You evaluate the candidate's coding skills."
    )
    tech_agent = TechInterviewAgent(
        role="Technical Interview",
        goal="Conduct technical interviews.",
        backstory="You assess the candidate's technical depth."
    )
    hr_agent = HRInterviewAgent(
        role="HR Interview",
        goal="Conduct HR interviews.",
        backstory="You evaluate the candidate's fit for the company culture."
    )
    offer_agent = OfferLetterAgent(
        role="Offer Letter",
        goal="Generate and send offer letters.",
        backstory="You formalize the hiring decision."
    )
    reject_agent = RejectionAgent(
        role="Rejection",
        goal="Send rejection emails.",
        backstory="You notify candidates who are not selected."
    )

    # Form Intake
    form_result = form_agent.run()
    print("Form Intake Result:", form_result)

    # Skill Match
    skill_result = skill_agent.run(**form_result)
    print("Skill Match Result:", skill_result)
    if not skill_result.get("skills_matched"):
        reject_agent.run()
        return

    # Coding Test
    coding_test = code_agent.run()
    print("Coding Question:", coding_test["question"])
    candidate_code = input("Enter your code answer:\n")
    coding_eval = code_agent.run(candidate_answer=candidate_code)
    print("Coding Evaluation:", coding_eval["evaluation"])
    if "No" in coding_eval["evaluation"]:
        reject_agent.run()
        return

    # Technical Interview
    tech_test = tech_agent.run()
    print("Technical Interview Question:", tech_test["question"])
    candidate_tech = input("Enter your technical answer:\n")
    tech_eval = tech_agent.run(candidate_answer=candidate_tech)
    print("Technical Evaluation:", tech_eval["evaluation"])
    if "No" in tech_eval["evaluation"]:
        reject_agent.run()
        return

    # HR Interview
    hr_result = hr_agent.run()
    print("HR Interview Result:", hr_result)
    if not hr_result.get("hr_interview_passed"):
        reject_agent.run()
        return

    # Offer Letter
    offer_result = offer_agent.run()
    print("Offer Letter Result:", offer_result)

if __name__ == "__main__":
    main()
