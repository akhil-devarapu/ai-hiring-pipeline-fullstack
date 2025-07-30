from crewai import Task

def form_intake_task(agent):
    return Task(
        agent=agent,
        description="Collect candidate info and resume.",
        expected_output="A dictionary with candidate details (name, email, phone, role, skills, resume_filename)."
    )

def skill_match_task(agent):
    return Task(
        agent=agent,
        description="Check if candidate skills match the job.",
        expected_output="A boolean indicating if the candidate matches, and a reason if not."
    )

def coding_test_task(agent):
    return Task(
        agent=agent,
        description="Send and grade coding test.",
        expected_output="A boolean indicating pass/fail and the score."
    )

def tech_interview_task(agent):
    return Task(
        agent=agent,
        description="Conduct technical interview.",
        expected_output="A boolean indicating pass/fail and interview notes."
    )

def hr_interview_task(agent):
    return Task(
        agent=agent,
        description="Conduct HR interview.",
        expected_output="A boolean indicating pass/fail and HR notes."
    )

def offer_letter_task(agent):
    return Task(
        agent=agent,
        description="Generate and send offer letter.",
        expected_output="Confirmation that the offer letter was sent."
    )

def rejection_task(agent):
    return Task(
        agent=agent,
        description="Send rejection email.",
        expected_output="Confirmation that the rejection email was sent."
    ) 