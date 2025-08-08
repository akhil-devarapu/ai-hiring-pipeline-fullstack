from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message
import os
import json
from dotenv import load_dotenv
load_dotenv()

# Import utils with fallbacks
try:
    from utils.resume_parser import parse_resume
    print("[INFO] resume_parser successfully imported")
except ImportError as e:
    print(f"Warning: resume_parser not available. Using fallback. Error: {e}")
    def parse_resume(file_path):
        return f"Resume content from {file_path}"

try:
    from utils.email_utils import send_email
    print("[INFO] email_utils successfully imported")
except ImportError as e:
    print(f"Warning: email_utils not available. Using fallback. Error: {e}")
    def send_email(subject, recipients, body, mail):
        print(f"[EMAIL] {subject} to {recipients}: {body}")

try:
    from utils.judge0_utils import submit_code, get_result
    print("[INFO] judge0_utils successfully imported")
except ImportError as e:
    print(f"Warning: judge0_utils not available. Using fallback. Error: {e}")
    def submit_code(code, language, stdin=""):
        return "demo_token"
    def get_result(token):
        return "Demo output"

import uuid
import tempfile
import openai
from datetime import datetime

# CrewAI imports
try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = True
    print("[INFO] CrewAI successfully imported")
except ImportError as e:
    print(f"Warning: CrewAI not available. Using fallback mode. Error: {e}")
    CREWAI_AVAILABLE = False
    # Create dummy classes for fallback
    class Agent:
        def __init__(self, **kwargs):
            pass
    class Task:
        def __init__(self, **kwargs):
            pass
    class Crew:
        def __init__(self, **kwargs):
            pass
        def kickoff(self):
            return "Fallback response"
    class Process:
        sequential = "sequential"

try:
    from langchain_openai import ChatOpenAI
    print("[INFO] langchain_openai successfully imported")
except ImportError:
    try:
        from langchain.chat_models import ChatOpenAI
        print("[INFO] langchain.chat_models successfully imported")
    except ImportError:
        try:
            from langchain_community.chat_models import ChatOpenAI
            print("[INFO] langchain_community.chat_models successfully imported")
        except ImportError:
            print("Warning: ChatOpenAI not available. Using fallback.")
            class ChatOpenAI:
                def __init__(self, **kwargs):
                    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mail = Mail(app)
openai.api_key = os.getenv("OPENAI_API_KEY")

JD = "We are looking for a Python developer."

# File to store candidate states persistently
CANDIDATE_STATES_FILE = 'candidate_states.json'

def load_candidate_states():
    """Load candidate states from file"""
    try:
        if os.path.exists(CANDIDATE_STATES_FILE):
            with open(CANDIDATE_STATES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Loaded {len(data)} candidate states from file")
                return data
    except Exception as e:
        print(f"Error loading candidate states: {e}")
        try:
            if os.path.exists(CANDIDATE_STATES_FILE):
                backup_file = f"{CANDIDATE_STATES_FILE}.backup"
                os.rename(CANDIDATE_STATES_FILE, backup_file)
                print(f"Backed up corrupted file to {backup_file}")
        except:
            pass
    return {}

def save_candidate_states(states):
    """Save candidate states to file"""
    try:
        backup_file = f"{CANDIDATE_STATES_FILE}.backup"
        if os.path.exists(CANDIDATE_STATES_FILE):
            if os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                    print(f"[DEBUG] Removed old backup file: {backup_file}")
                except Exception as e:
                    print(f"[ERROR] Could not remove backup file: {e}")
            try:
                os.rename(CANDIDATE_STATES_FILE, backup_file)
                print(f"[DEBUG] Backed up candidate states file to: {backup_file}")
            except Exception as e:
                print(f"[ERROR] Could not backup candidate states file: {e}")
        with open(CANDIDATE_STATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(states, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Saved {len(states)} candidate states to file: {CANDIDATE_STATES_FILE}")
    except Exception as e:
        print(f"[ERROR] Error saving candidate states: {e}")
        try:
            backup_file = f"{CANDIDATE_STATES_FILE}.backup"
            if os.path.exists(backup_file):
                os.rename(backup_file, CANDIDATE_STATES_FILE)
                print("[INFO] Restored candidate states from backup file after save failure.")
        except Exception as e2:
            print(f"[ERROR] Could not restore from backup file: {e2}")

def check_and_mark_link_used(token, link_type):
    """
    Check if a link is valid and if the test/interview has been completed.
    Returns (is_valid, is_completed)
    """
    state = candidate_states.get(token)
    if not state:
        return False, False
    
    # Check if this specific test/interview has been completed
    completed_key = f'{link_type}_completed'
    if state.get(completed_key, False):
        return True, True  # Link exists and has been completed
    
    return True, False  # Link exists but not completed yet

def mark_test_completed(token, link_type):
    """Mark a test/interview as completed"""
    state = candidate_states.get(token)
    if state:
        state[f'{link_type}_completed'] = True
        state[f'{link_type}_completed_at'] = datetime.now().isoformat()
        candidate_states[token] = state
        save_candidate_states(candidate_states)

# Load existing states
candidate_states = load_candidate_states()

if not candidate_states:
    print("No candidate states loaded from file, starting with empty state")
    candidate_states = {}

if not os.path.exists(CANDIDATE_STATES_FILE):
    print(f"Creating new candidate states file: {CANDIDATE_STATES_FILE}")
    save_candidate_states(candidate_states)

# CrewAI Agents
def create_resume_screening_agent():
    """Agent for screening resumes and initial candidate evaluation"""
    if not CREWAI_AVAILABLE:
        return None
    return Agent(
        role='Resume Screening Specialist',
        goal='Evaluate candidate resumes and determine if they match job requirements',
        backstory="""You are an expert HR professional with years of experience in technical hiring. 
        You excel at analyzing resumes and determining candidate fit for technical positions.""",
        verbose=True,
        allow_delegation=False,
        llm=ChatOpenAI(model="gpt-4", temperature=0.1)
    )

def create_coding_assessment_agent():
    """Agent for creating and evaluating coding tests"""
    if not CREWAI_AVAILABLE:
        return None
    return Agent(
        role='Coding Assessment Specialist',
        goal='Create coding questions and evaluate candidate solutions with detailed analysis',
        backstory="""You are a senior software engineer and technical interviewer. 
        You have extensive experience in evaluating code quality, efficiency, and best practices.""",
        verbose=True,
        allow_delegation=False,
        llm=ChatOpenAI(model="gpt-4", temperature=0.1)
    )

def create_technical_interview_agent():
    """Agent for conducting technical interviews"""
    if not CREWAI_AVAILABLE:
        return None
    return Agent(
        role='Technical Interviewer',
        goal='Conduct technical interviews and evaluate candidate knowledge depth',
        backstory="""You are a senior technical interviewer with expertise in software engineering. 
        You excel at asking probing questions and evaluating technical depth.""",
        verbose=True,
        allow_delegation=False,
        llm=ChatOpenAI(model="gpt-4", temperature=0.1)
    )

def create_hr_interview_agent():
    """Agent for conducting HR interviews"""
    if not CREWAI_AVAILABLE:
        return None
    return Agent(
        role='HR Interviewer',
        goal='Conduct HR interviews and evaluate cultural fit and professionalism',
        backstory="""You are an experienced HR professional specializing in cultural fit assessment. 
        You excel at evaluating communication skills, professionalism, and cultural alignment.""",
        verbose=True,
        allow_delegation=False,
        llm=ChatOpenAI(model="gpt-4", temperature=0.1)
    )

def create_offer_letter_agent():
    """Agent for generating offer letters"""
    if not CREWAI_AVAILABLE:
        return None
    return Agent(
        role='Offer Letter Specialist',
        goal='Generate professional offer letters for successful candidates',
        backstory="""You are an HR specialist who creates compelling and professional offer letters. 
        You ensure all legal requirements are met while maintaining a warm, welcoming tone.""",
        verbose=True,
        allow_delegation=False,
        llm=ChatOpenAI(model="gpt-4", temperature=0.1)
    )

# Flask Routes
@app.route('/form', methods=['GET', 'POST'])
def candidate_form():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        skills = request.form['skills']
        resume = request.files['resume']
        
        if not (name and email and skills and resume and resume.filename):
            flash('All fields are required!', 'danger')
            return redirect(request.url)
        
        filename = f"{email}_{resume.filename}"
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        resume.save(resume_path)
        resume_text = parse_resume(resume_path)
        
        # Set JD to entry level Python developer
        JD = "Entry level Python developer"
        
        # If 'python' is in skills, auto-select
        if 'python' in skills.lower():
            # Generate coding question and expected output using CrewAI
            if CREWAI_AVAILABLE:
                try:
                    question_task = Task(
                        description="""
                        Generate a unique, easy-level coding question for a Python developer interview.
                        The question should be:
                        1. Clear and well-defined
                        2. Appropriate for entry-level to mid-level developers
                        3. Test basic programming concepts
                        4. Have a clear expected output
                        
                        Return the response in this exact JSON format:
                        {
                            "question": "Write a function to add two numbers and return the result.",
                            "expected_output": "5 (for input 2, 3)"
                        }
                        """,
                        agent=create_coding_assessment_agent(),
                        expected_output="JSON with 'question' and 'expected_output' fields"
                    )
                    question_crew = Crew(
                        agents=[create_coding_assessment_agent()],
                        tasks=[question_task],
                        verbose=True,
                        process=Process.sequential
                    )
                    result = question_crew.kickoff()
                    print(f"[DEBUG] Question generation result: {result}")
                    
                    import re
                    import json
                    try:
                        if isinstance(result, str):
                            # Look for JSON in the result
                            json_match = re.search(r'\{.*\}', result, re.DOTALL)
                            if json_match:
                                parsed_result = json.loads(json_match.group())
                                question = parsed_result.get('question', "Write a function to add two numbers.")
                                expected_output = parsed_result.get('expected_output', "5 (for input 2, 3)")
                            else:
                                # Fallback to regex
                                question_match = re.search(r'"question":\s*"([^"]+)"', result)
                                question = question_match.group(1) if question_match else "Write a function to add two numbers."
                                expected_output_match = re.search(r'"expected_output":\s*"([^"]+)"', result)
                                expected_output = expected_output_match.group(1) if expected_output_match else "5 (for input 2, 3)"
                        else:
                            question = "Write a function to add two numbers."
                            expected_output = "5 (for input 2, 3)"
                    except Exception as e:
                        print(f"[ERROR] Error parsing question result: {e}")
                        question = "Write a function to add two numbers."
                        expected_output = "5 (for input 2, 3)"
                except Exception as e:
                    print(f"[ERROR] Error generating question: {e}")
                    question = "Write a function to add two numbers."
                    expected_output = "5 (for input 2, 3)"
            else:
                # Fallback when CrewAI is not available
                question = "Write a function to add two numbers and return the result."
                expected_output = "5 (for input 2, 3)"
            decision = "YES"
        else:
            question = None
            expected_output = None
            decision = "NO"
        
        if decision == "YES":
            # Generate a new token for this candidate
            token = str(uuid.uuid4())
            print(f"[INFO] Candidate {name} ({email}) auto-selected. Token: {token}")
            candidate_states[token] = {
                'name': name,
                'email': email,
                'resume_text': resume_text,
                'skills': skills,
                'question': question,
                'expected_output': expected_output,
                'coding_test_completed': False,
                'tech_interview_completed': False,
                'hr_interview_completed': False
            }
            save_candidate_states(candidate_states)
            
            coding_link = url_for('coding_test', token=token, _external=True)
            print(f"[INFO] Coding test link generated: {coding_link}")
            try:
                send_email(
                    subject='Coding Assessment Link',
                    recipients=[email],
                    body=f"Hi {name},\n\nYou have been shortlisted! Please take your coding test here: {coding_link}\n\nBest,\nHiring Team",
                    mail=mail
                )
                flash('You have been shortlisted! Check your email for the coding test link.', 'success')
            except Exception as e:
                print(f"[ERROR] Error sending email: {e}")
                flash('You have been shortlisted! Please check your email for the coding test link.', 'success')
        else:
            try:
                send_email(
                    subject='Application Update',
                    recipients=[email],
                    body=f"Hi {name},\n\nThank you for applying. Unfortunately, you do not match our requirements at this time.\n\nBest,\nHiring Team",
                    mail=mail
                )
                flash('Thank you for applying. You will receive an update by email.', 'info')
            except Exception as e:
                print(f"[ERROR] Error sending email: {e}")
                flash('Thank you for applying. You will receive an update by email.', 'info')
        
        return redirect(url_for('candidate_form'))
    
    return render_template('form.html')

@app.route('/coding-test/<token>', methods=['GET', 'POST'])
def coding_test(token):
    print(f"Accessing coding test with token: {token}")
    
    # Check if link is valid and if test is completed
    is_valid, is_completed = check_and_mark_link_used(token, 'coding_test')
    
    if not is_valid:
        return render_template('error.html', 
                             message="Invalid or expired coding test link.",
                             suggestion="Please check your email for the correct link or contact support.")
    
    if is_completed:
        # If test is completed, show the result
        state = candidate_states.get(token)
        if state and 'coding_analysis' in state:
            analysis_result = state['coding_analysis']
            if analysis_result['recommendation'] == 'PASS':
                return render_template('coding_result.html', 
                                    passed=True, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'],
                                    next_stage="Technical Interview")
            else:
                return render_template('coding_result.html', 
                                    passed=False, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'])
    
    state = candidate_states.get(token)
    print(f"Found state for token {token}: {state.get('name', 'Unknown')}")
    
    # Ensure question exists
    question = state.get('question')
    if not question:
        # Use CrewAI to generate question
        if CREWAI_AVAILABLE:
            try:
                question_task = Task(
                    description="""
                    Generate a unique, easy-level coding question for a Python developer interview.
                    The question should be:
                    1. Clear and well-defined
                    2. Appropriate for entry-level to mid-level developers
                    3. Test basic programming concepts
                    4. Have a clear expected output
                    
                    Return the response in this exact JSON format:
                    {
                        "question": "Write a function to add two numbers and return the result.",
                        "expected_output": "5 (for input 2, 3)"
                    }
                    """,
                    agent=create_coding_assessment_agent(),
                    expected_output="JSON with 'question' and 'expected_output' fields"
                )
                
                question_crew = Crew(
                    agents=[create_coding_assessment_agent()],
                    tasks=[question_task],
                    verbose=True,
                    process=Process.sequential
                )
                
                result = question_crew.kickoff()
                print(f"[DEBUG] Question generation result: {result}")
                
                # Parse the result to extract question
                import re
                import json
                try:
                    # Try to parse as JSON first
                    if isinstance(result, str):
                        # Look for JSON in the result
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            parsed_result = json.loads(json_match.group())
                            question = parsed_result.get('question', "Write a function to add two numbers.")
                        else:
                            # Fallback to regex
                            question_match = re.search(r'"question":\s*"([^"]+)"', result)
                            question = question_match.group(1) if question_match else "Write a function to add two numbers."
                    else:
                        question = "Write a function to add two numbers."
                except Exception as e:
                    print(f"[ERROR] Error parsing question result: {e}")
                    question = "Write a function to add two numbers."
            except Exception as e:
                print(f"[ERROR] Error generating question: {e}")
                question = "Write a function to add two numbers."
        else:
            # Fallback question when CrewAI is not available
            question = "Write a function to add two numbers and return the result."
        
        state['question'] = question
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    
    if request.method == 'POST':
        code = request.form['code']
        language = request.form['language']
        
        # Submit code and get output
        try:
            submission_token = submit_code(code, language, stdin="2 3\n")
            output = get_result(submission_token)
        except Exception as e:
            print(f"[ERROR] Error submitting code: {e}")
            output = "Error executing code"
        
        # Use CrewAI to analyze the coding solution
        if CREWAI_AVAILABLE:
            try:
                evaluation_task = Task(
                    description=f"""
                    Evaluate the following coding solution:
                    
                    Question: {question}
                    Candidate's Code: {code}
                    Language: {language}
                    
                    Provide a comprehensive evaluation with:
                    1. Overall score (0-100)
                    2. Detailed feedback on correctness, quality, efficiency, edge cases, and documentation
                    3. Specific suggestions for improvement
                    4. Final recommendation: PASS (if score >= 80) or FAIL (if score < 80)
                    
                    Return the response in this exact JSON format:
                    {{
                        "score": 85,
                        "feedback": "Detailed feedback here...",
                        "recommendation": "PASS"
                    }}
                    """,
                    agent=create_coding_assessment_agent(),
                    expected_output="JSON with score, feedback, and recommendation"
                )
                
                evaluation_crew = Crew(
                    agents=[create_coding_assessment_agent()],
                    tasks=[evaluation_task],
                    verbose=True,
                    process=Process.sequential
                )
                
                result = evaluation_crew.kickoff()
                print(f"[DEBUG] Evaluation result: {result}")
                
                # Parse the result
                import re
                import json
                try:
                    if isinstance(result, str):
                        # Look for JSON in the result
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            parsed_result = json.loads(json_match.group())
                            score = parsed_result.get('score', 0)
                            recommendation = parsed_result.get('recommendation', 'FAIL')
                            feedback = parsed_result.get('feedback', result)
                        else:
                            # Fallback to regex
                            score_match = re.search(r'"score":\s*(\d+)', result)
                            score = int(score_match.group(1)) if score_match else 0
                            recommendation_match = re.search(r'"recommendation":\s*"(PASS|FAIL)"', result)
                            recommendation = recommendation_match.group(1) if recommendation_match else "FAIL"
                            feedback = result
                    else:
                        score = 0
                        recommendation = "FAIL"
                        feedback = str(result)
                except Exception as e:
                    print(f"[ERROR] Error parsing evaluation result: {e}")
                    score = 0
                    recommendation = "FAIL"
                    feedback = str(result)
            except Exception as e:
                print(f"[ERROR] Error in evaluation: {e}")
                score = 0
                recommendation = "FAIL"
                feedback = f"Error during evaluation: {str(e)}"
        else:
            # Fallback evaluation when CrewAI is not available
            # Simple evaluation based on code length and basic checks
            score = 75  # Default score
            if 'def' in code and 'return' in code:
                score = 85
            if 'print' in code:
                score += 5
            if score >= 80:
                recommendation = "PASS"
            else:
                recommendation = "FAIL"
            feedback = f"Fallback evaluation: Code contains basic Python structure. Score: {score}/100"
        
        analysis_result = {
            'score': score,
            'feedback': feedback,
            'recommendation': recommendation
        }
        
        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        
        # Store analysis results in state
        state['coding_analysis'] = analysis_result
        candidate_states[token] = state
        save_candidate_states(candidate_states)
        
        print(f"[INFO] Coding test submitted for token {token}. Score: {analysis_result['score']}, Recommendation: {analysis_result['recommendation']}")
        
        if analysis_result['recommendation'] == 'PASS':
            mark_test_completed(token, 'coding_test')
            tech_link = url_for('tech_interview', token=token, _external=True)
            try:
                send_email(
                    subject='Technical Interview Link',
                    recipients=[email],
                    body=f"Hi {name},\n\nCongratulations! You passed the coding test with a score of {analysis_result['score']}/100. Attend your technical interview here: {tech_link}\n\nBest,\nHiring Team",
                    mail=mail
                )
            except Exception as e:
                print(f"[ERROR] Error sending email: {e}")
            
            return render_template('coding_result.html', 
                                passed=True, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'],
                                next_stage="Technical Interview")
        else:
            try:
                send_email(
                    subject='Application Update',
                    recipients=[email],
                    body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not pass the coding test. Your score was {analysis_result['score']}/100.\n\nBest,\nHiring Team",
                    mail=mail
                )
            except Exception as e:
                print(f"[ERROR] Error sending email: {e}")
            
            return render_template('coding_result.html', 
                                passed=False, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'])
    
    return render_template('coding_test.html', question=question)

@app.route('/tech-interview/<token>', methods=['GET', 'POST'])
def tech_interview(token):
    print(f"Accessing tech interview with token: {token}")
    
    # Check if link is valid and if interview is completed
    is_valid, is_completed = check_and_mark_link_used(token, 'tech_interview')
    
    if not is_valid:
        return render_template('error.html', 
                             message="Invalid or expired technical interview link.",
                             suggestion="Please check your email for the correct link or contact support.")
    
    if is_completed:
        # If interview is completed, show the result
        state = candidate_states.get(token)
        if state and 'tech_analysis' in state:
            analysis_result = state['tech_analysis']
            if analysis_result['recommendation'] == 'PASS':
                return render_template('tech_result.html', 
                                    passed=True, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'],
                                    next_stage="HR Interview")
            else:
                return render_template('tech_result.html', 
                                    passed=False, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'])
    
    state = candidate_states.get(token)
    print(f"Found state for token {token}: {state.get('name', 'Unknown')}")
    
    # Ensure question exists
    question = state.get('tech_question')
    if not question:
        # Use CrewAI to generate question
        if CREWAI_AVAILABLE:
            try:
                question_task = Task(
                    description=f"""
                    Generate a technical interview question for a Python developer based on their resume:
                    
                    Resume: {state.get('resume_text', '')}
                    Skills: {state.get('skills', '')}
                    
                    The question should be:
                    1. Relevant to their background
                    2. Test technical depth
                    3. Appropriate for their experience level
                    4. Clear and well-structured
                    
                    Return the response in this exact JSON format:
                    {{
                        "question": "Explain the difference between a list and a tuple in Python."
                    }}
                    """,
                    agent=create_technical_interview_agent(),
                    expected_output="JSON with 'question' field"
                )
                
                question_crew = Crew(
                    agents=[create_technical_interview_agent()],
                    tasks=[question_task],
                    verbose=True,
                    process=Process.sequential
                )
                
                result = question_crew.kickoff()
                print(f"[DEBUG] Tech question generation result: {result}")
                
                # Parse the result to extract question
                import re
                import json
                try:
                    if isinstance(result, str):
                        # Look for JSON in the result
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            parsed_result = json.loads(json_match.group())
                            question = parsed_result.get('question', "Explain the difference between a list and a tuple in Python.")
                        else:
                            # Fallback to regex
                            question_match = re.search(r'"question":\s*"([^"]+)"', result)
                            question = question_match.group(1) if question_match else "Explain the difference between a list and a tuple in Python."
                    else:
                        question = "Explain the difference between a list and a tuple in Python."
                except Exception as e:
                    print(f"[ERROR] Error parsing tech question result: {e}")
                    question = "Explain the difference between a list and a tuple in Python."
            except Exception as e:
                print(f"[ERROR] Error generating tech question: {e}")
                question = "Explain the difference between a list and a tuple in Python."
        else:
            # Fallback question when CrewAI is not available
            question = "Explain the difference between a list and a tuple in Python."
        
        state['tech_question'] = question
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    else:
        question = state['tech_question']
    
    if request.method == 'POST':
        answer = request.form['answer']
        
        # Use CrewAI to analyze the technical answer
        if CREWAI_AVAILABLE:
            try:
                evaluation_task = Task(
                    description=f"""
                    Evaluate the following technical interview answer:
                    
                    Question: {question}
                    Candidate's Answer: {answer}
                    
                    Provide a comprehensive evaluation with:
                    1. Overall score (0-100)
                    2. Detailed feedback on accuracy, completeness, depth, clarity, and practical application
                    3. Specific suggestions for improvement
                    4. Final recommendation: PASS (if score >= 80) or FAIL (if score < 80)
                    
                    Return the response in this exact JSON format:
                    {{
                        "score": 85,
                        "feedback": "Detailed feedback here...",
                        "recommendation": "PASS"
                    }}
                    """,
                    agent=create_technical_interview_agent(),
                    expected_output="JSON with score, feedback, and recommendation"
                )
                
                evaluation_crew = Crew(
                    agents=[create_technical_interview_agent()],
                    tasks=[evaluation_task],
                    verbose=True,
                    process=Process.sequential
                )
                
                result = evaluation_crew.kickoff()
                print(f"[DEBUG] Tech evaluation result: {result}")
                
                # Parse the result
                import re
                import json
                try:
                    if isinstance(result, str):
                        # Look for JSON in the result
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            parsed_result = json.loads(json_match.group())
                            score = parsed_result.get('score', 0)
                            recommendation = parsed_result.get('recommendation', 'FAIL')
                            feedback = parsed_result.get('feedback', result)
                        else:
                            # Fallback to regex
                            score_match = re.search(r'"score":\s*(\d+)', result)
                            score = int(score_match.group(1)) if score_match else 0
                            recommendation_match = re.search(r'"recommendation":\s*"(PASS|FAIL)"', result)
                            recommendation = recommendation_match.group(1) if recommendation_match else "FAIL"
                            feedback = result
                    else:
                        score = 0
                        recommendation = "FAIL"
                        feedback = str(result)
                except Exception as e:
                    print(f"[ERROR] Error parsing tech evaluation result: {e}")
                    score = 0
                    recommendation = "FAIL"
                    feedback = str(result)
            except Exception as e:
                print(f"[ERROR] Error in tech evaluation: {e}")
                score = 0
                recommendation = "FAIL"
                feedback = f"Error during evaluation: {str(e)}"
        else:
            # Fallback evaluation when CrewAI is not available
            # Simple evaluation based on answer length and keywords
            score = 70  # Default score
            if len(answer) > 50:
                score += 10
            if 'list' in answer.lower() and 'tuple' in answer.lower():
                score += 10
            if 'mutable' in answer.lower() or 'immutable' in answer.lower():
                score += 10
            if score >= 80:
                recommendation = "PASS"
            else:
                recommendation = "FAIL"
            feedback = f"Fallback evaluation: Answer length and content analysis. Score: {score}/100"
        
        analysis_result = {
            'score': score,
            'feedback': feedback,
            'recommendation': recommendation
        }
        
        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        
        # Store analysis results in state
        state['tech_analysis'] = analysis_result
        candidate_states[token] = state
        save_candidate_states(candidate_states)
        
        print(f"[INFO] Tech interview submitted for token {token}. Score: {analysis_result['score']}, Recommendation: {analysis_result['recommendation']}")
        
        if analysis_result['recommendation'] == 'PASS':
            mark_test_completed(token, 'tech_interview')
            hr_link = url_for('hr_interview', token=token, _external=True)
            try:
                send_email(
                    subject='HR Interview Link',
                    recipients=[email],
                    body=f"Hi {name},\n\nCongratulations! You passed the technical interview with a score of {analysis_result['score']}/100. Attend your HR interview here: {hr_link}\n\nBest,\nHiring Team",
                    mail=mail
                )
            except Exception as e:
                print(f"[ERROR] Error sending email: {e}")
            
            return render_template('tech_result.html', 
                                passed=True, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'],
                                next_stage="HR Interview")
        else:
            try:
                send_email(
                    subject='Application Update',
                    recipients=[email],
                    body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not pass the technical interview. Your score was {analysis_result['score']}/100.\n\nBest,\nHiring Team",
                    mail=mail
                )
            except Exception as e:
                print(f"[ERROR] Error sending email: {e}")
            
            return render_template('tech_result.html', 
                                passed=False, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'])
    
    return render_template('tech_interview.html', question=question)

@app.route('/hr-interview/<token>', methods=['GET', 'POST'])
def hr_interview(token):
    print(f"Accessing HR interview with token: {token}")
    
    # Check if link is valid and if interview is completed
    is_valid, is_completed = check_and_mark_link_used(token, 'hr_interview')
    
    if not is_valid:
        return render_template('error.html', 
                             message="Invalid or expired HR interview link.",
                             suggestion="Please check your email for the correct link or contact support.")
    
    if is_completed:
        # If interview is completed, show the result
        state = candidate_states.get(token)
        if state and 'hr_analysis' in state:
            analysis_result = state['hr_analysis']
            if analysis_result['recommendation'] == 'PASS':
                offer_link = url_for('view_offer_letter', token=token, _external=True)
                return render_template('hr_result.html', 
                                    passed=True, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'],
                                    offer_link=offer_link)
            else:
                return render_template('hr_result.html', 
                                    passed=False, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'])
    
    state = candidate_states.get(token)
    print(f"Found state for token {token}: {state.get('name', 'Unknown')}")
    
    # Ensure question exists
    question = state.get('hr_question')
    if not question:
        # Use CrewAI to generate question
        if CREWAI_AVAILABLE:
            try:
                question_task = Task(
                    description="""
                    Generate an HR interview question for a job candidate.
                    The question should be:
                    1. Relevant to workplace scenarios
                    2. Test communication skills
                    3. Assess cultural fit
                    4. Professional and appropriate
                    
                    Return the response in this exact JSON format:
                    {
                        "question": "Tell me about a challenging situation you faced at work and how you handled it."
                    }
                    """,
                    agent=create_hr_interview_agent(),
                    expected_output="JSON with 'question' field"
                )
                
                question_crew = Crew(
                    agents=[create_hr_interview_agent()],
                    tasks=[question_task],
                    verbose=True,
                    process=Process.sequential
                )
                
                result = question_crew.kickoff()
                print(f"[DEBUG] HR question generation result: {result}")
                
                # Parse the result to extract question
                import re
                import json
                try:
                    if isinstance(result, str):
                        # Look for JSON in the result
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            parsed_result = json.loads(json_match.group())
                            question = parsed_result.get('question', "Tell me about a challenging situation you faced at work and how you handled it.")
                        else:
                            # Fallback to regex
                            question_match = re.search(r'"question":\s*"([^"]+)"', result)
                            question = question_match.group(1) if question_match else "Tell me about a challenging situation you faced at work and how you handled it."
                    else:
                        question = "Tell me about a challenging situation you faced at work and how you handled it."
                except Exception as e:
                    print(f"[ERROR] Error parsing HR question result: {e}")
                    question = "Tell me about a challenging situation you faced at work and how you handled it."
            except Exception as e:
                print(f"[ERROR] Error generating HR question: {e}")
                question = "Tell me about a challenging situation you faced at work and how you handled it."
        else:
            # Fallback question when CrewAI is not available
            question = "Tell me about a challenging situation you faced at work and how you handled it."
        
        state['hr_question'] = question
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    else:
        question = state['hr_question']
    
    if request.method == 'POST':
        answer = request.form['answer']
        
        # Use CrewAI to analyze the HR answer
        if CREWAI_AVAILABLE:
            try:
                evaluation_task = Task(
                    description=f"""
                    Evaluate the following HR interview answer:
                    
                    Question: {question}
                    Candidate's Answer: {answer}
                    
                    Provide a comprehensive evaluation with:
                    1. Overall score (0-100)
                    2. Detailed feedback on relevance, professionalism, clarity, honesty, and cultural fit
                    3. Specific suggestions for improvement
                    4. Final recommendation: PASS (if score >= 80) or FAIL (if score < 80)
                    
                    Return the response in this exact JSON format:
                    {{
                        "score": 85,
                        "feedback": "Detailed feedback here...",
                        "recommendation": "PASS"
                    }}
                    """,
                    agent=create_hr_interview_agent(),
                    expected_output="JSON with score, feedback, and recommendation"
                )
                
                evaluation_crew = Crew(
                    agents=[create_hr_interview_agent()],
                    tasks=[evaluation_task],
                    verbose=True,
                    process=Process.sequential
                )
                
                result = evaluation_crew.kickoff()
                print(f"[DEBUG] HR evaluation result: {result}")
                
                # Parse the result
                import re
                import json
                try:
                    if isinstance(result, str):
                        # Look for JSON in the result
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            parsed_result = json.loads(json_match.group())
                            score = parsed_result.get('score', 0)
                            recommendation = parsed_result.get('recommendation', 'FAIL')
                            feedback = parsed_result.get('feedback', result)
                        else:
                            # Fallback to regex
                            score_match = re.search(r'"score":\s*(\d+)', result)
                            score = int(score_match.group(1)) if score_match else 0
                            recommendation_match = re.search(r'"recommendation":\s*"(PASS|FAIL)"', result)
                            recommendation = recommendation_match.group(1) if recommendation_match else "FAIL"
                            feedback = result
                    else:
                        score = 0
                        recommendation = "FAIL"
                        feedback = str(result)
                except Exception as e:
                    print(f"[ERROR] Error parsing HR evaluation result: {e}")
                    score = 0
                    recommendation = "FAIL"
                    feedback = str(result)
            except Exception as e:
                print(f"[ERROR] Error in HR evaluation: {e}")
                score = 0
                recommendation = "FAIL"
                feedback = f"Error during evaluation: {str(e)}"
        else:
            # Fallback evaluation when CrewAI is not available
            # Simple evaluation based on answer length and keywords
            score = 70  # Default score
            if len(answer) > 100:
                score += 15
            if 'challenge' in answer.lower() or 'difficult' in answer.lower():
                score += 5
            if 'solution' in answer.lower() or 'resolve' in answer.lower():
                score += 5
            if 'team' in answer.lower() or 'collaboration' in answer.lower():
                score += 5
            if score >= 80:
                recommendation = "PASS"
            else:
                recommendation = "FAIL"
            feedback = f"Fallback evaluation: Answer length and content analysis. Score: {score}/100"
        
        analysis_result = {
            'score': score,
            'feedback': feedback,
            'recommendation': recommendation
        }
        
        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        
        # Store analysis results in state
        state['hr_analysis'] = analysis_result
        candidate_states[token] = state
        save_candidate_states(candidate_states)
        
        print(f"[INFO] HR interview submitted for token {token}. Score: {analysis_result['score']}, Recommendation: {analysis_result['recommendation']}")
        
        if analysis_result['recommendation'] == 'PASS':
            mark_test_completed(token, 'hr_interview')
            # Use CrewAI to generate offer letter
            if CREWAI_AVAILABLE:
                try:
                    offer_task = Task(
                        description=f"""
                        Generate a professional offer letter for the successful candidate:
                        
                        Name: {name}
                        Email: {email}
                        Position: Python Developer
                        
                        The offer letter should:
                        1. Be professional and welcoming
                        2. Include all necessary details
                        3. Be formatted as HTML
                        4. Have a warm, positive tone
                        5. Include next steps for the candidate
                        
                        Return the response as HTML formatted offer letter.
                        """,
                        agent=create_offer_letter_agent(),
                        expected_output="HTML formatted offer letter"
                    )
                    
                    offer_crew = Crew(
                        agents=[create_offer_letter_agent()],
                        tasks=[offer_task],
                        verbose=True,
                        process=Process.sequential
                    )
                    
                    offer_result = offer_crew.kickoff()
                    
                    try:
                        msg = Message(
                            subject='🎉 Congratulations! Your Offer Letter',
                            recipients=[email],
                            body=f"Hi {name},\n\nCongratulations! You have cleared all rounds with a score of {analysis_result['score']}/100. Please find your offer letter in the email body.\n\nBest,\nHiring Team",
                            html=offer_result
                        )
                        mail.send(msg)
                    except Exception as e:
                        print(f"[ERROR] Error sending offer email: {e}")
                    
                    # Add offer letter link to the result
                    offer_link = url_for('view_offer_letter', token=token, _external=True)
                    print(f"[INFO] Candidate {name} passed HR interview. Offer letter link: {offer_link}")
                    return render_template('hr_result.html', 
                                        passed=True, 
                                        score=analysis_result['score'],
                                        feedback=analysis_result['feedback'],
                                        offer_link=offer_link)
                except Exception as e:
                    print(f"[ERROR] Error generating offer letter: {e}")
                    # If offer letter generation fails, still show success
                    offer_link = url_for('view_offer_letter', token=token, _external=True)
                    return render_template('hr_result.html', 
                                        passed=True, 
                                        score=analysis_result['score'],
                                        feedback=analysis_result['feedback'],
                                        offer_link=offer_link,
                                        email_error=True)
            else:
                # Fallback offer letter when CrewAI is not available
                try:
                    fallback_offer = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Offer Letter</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; }}
                            .header {{ text-align: center; margin-bottom: 30px; }}
                            .content {{ line-height: 1.6; }}
                            .signature {{ margin-top: 40px; }}
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h1>🎉 Congratulations!</h1>
                            <h2>Offer Letter</h2>
                        </div>
                        <div class="content">
                            <p>Dear {name},</p>
                            <p>We are delighted to offer you the position of <strong>Python Developer</strong> at our company.</p>
                            <p>Your exceptional performance throughout the interview process has demonstrated your technical skills, problem-solving abilities, and cultural fit with our organization.</p>
                            <p>We look forward to having you join our team and contribute to our continued success.</p>
                            <p>Please review the terms and conditions of this offer and let us know if you have any questions.</p>
                            <p>We are excited to welcome you aboard!</p>
                            <div class="signature">
                                <p>Best regards,<br>
                                Hiring Team</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    msg = Message(
                        subject='🎉 Congratulations! Your Offer Letter',
                        recipients=[email],
                        body=f"Hi {name},\n\nCongratulations! You have cleared all rounds with a score of {analysis_result['score']}/100. Please find your offer letter in the email body.\n\nBest,\nHiring Team",
                        html=fallback_offer
                    )
                    mail.send(msg)
                except Exception as e:
                    print(f"[ERROR] Error sending fallback offer email: {e}")
                
                offer_link = url_for('view_offer_letter', token=token, _external=True)
                return render_template('hr_result.html', 
                                    passed=True, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'],
                                    offer_link=offer_link)
        else:
            try:
                send_email(
                    subject='Application Update',
                    recipients=[email],
                    body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not clear the HR interview. Your score was {analysis_result['score']}/100.\n\nBest,\nHiring Team",
                    mail=mail
                )
            except Exception as e:
                print(f"[ERROR] Error sending email: {e}")
            
            return render_template('hr_result.html', 
                                passed=False, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'])
    
    return render_template('hr_interview.html', question=question)

@app.route('/offer-letter/<token>')
def view_offer_letter(token):
    """View offer letter in browser"""
    state = candidate_states.get(token)
    if not state:
        return render_template('error.html', 
                             message="Invalid or expired offer letter link.",
                             suggestion="Please check your email for the correct link or contact support.")
    
    # Check if candidate passed HR interview
    hr_analysis = state.get('hr_analysis')
    if not hr_analysis or hr_analysis.get('recommendation') != 'PASS':
        return render_template('error.html', 
                             message="Offer letter not available.",
                             suggestion="You need to pass the HR interview first to view the offer letter.")
    
    name = state.get('name', 'Candidate')
    email = state.get('email', 'candidate@example.com')
    
    # Generate offer letter using CrewAI
    if CREWAI_AVAILABLE:
        try:
            offer_task = Task(
                description=f"""
                Generate a professional offer letter for the successful candidate:
                
                Name: {name}
                Email: {email}
                Position: Python Developer
                
                The offer letter should:
                1. Be professional and welcoming
                2. Include all necessary details
                3. Be formatted as HTML
                4. Have a warm, positive tone
                5. Include next steps for the candidate
                
                Return the response as HTML formatted offer letter.
                """,
                agent=create_offer_letter_agent(),
                expected_output="HTML formatted offer letter"
            )
            
            offer_crew = Crew(
                agents=[create_offer_letter_agent()],
                tasks=[offer_task],
                verbose=True,
                process=Process.sequential
            )
            
            html_content = offer_crew.kickoff()
            return html_content
        except Exception as e:
            print(f"[ERROR] Error generating offer letter: {e}")
            # Return fallback offer letter
            fallback_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Offer Letter</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .content {{ line-height: 1.6; }}
                    .signature {{ margin-top: 40px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎉 Congratulations!</h1>
                    <h2>Offer Letter</h2>
                </div>
                <div class="content">
                    <p>Dear {name},</p>
                    <p>We are delighted to offer you the position of <strong>Python Developer</strong> at our company.</p>
                    <p>Your exceptional performance throughout the interview process has demonstrated your technical skills, problem-solving abilities, and cultural fit with our organization.</p>
                    <p>We look forward to having you join our team and contribute to our continued success.</p>
                    <p>Please review the terms and conditions of this offer and let us know if you have any questions.</p>
                    <p>We are excited to welcome you aboard!</p>
                    <div class="signature">
                        <p>Best regards,<br>
                        Hiring Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return fallback_html
    else:
        # Fallback offer letter when CrewAI is not available
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Offer Letter</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .content {{ line-height: 1.6; }}
                .signature {{ margin-top: 40px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Congratulations!</h1>
                <h2>Offer Letter</h2>
            </div>
            <div class="content">
                <p>Dear {name},</p>
                <p>We are delighted to offer you the position of <strong>Python Developer</strong> at our company.</p>
                <p>Your exceptional performance throughout the interview process has demonstrated your technical skills, problem-solving abilities, and cultural fit with our organization.</p>
                <p>We look forward to having you join our team and contribute to our continued success.</p>
                <p>Please review the terms and conditions of this offer and let us know if you have any questions.</p>
                <p>We are excited to welcome you aboard!</p>
                <div class="signature">
                    <p>Best regards,<br>
                    Hiring Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        return fallback_html

@app.route('/test-terminated')
def test_terminated():
    """Handle test termination due to violations"""
    return render_template('test_terminated.html')

@app.route('/debug/states')
def debug_states():
    """Debug endpoint to check candidate states"""
    return {
        'total_states': len(candidate_states),
        'tokens': list(candidate_states.keys()),
        'states': {k: {
            'name': v.get('name', 'Unknown'), 
            'email': v.get('email', 'Unknown'),
            'coding_test_used': v.get('coding_test_used', False),
            'tech_interview_used': v.get('tech_interview_used', False),
            'hr_interview_used': v.get('hr_interview_used', False)
        } for k, v in candidate_states.items()}
    }

@app.route('/')
def index():
    """Redirect to the application form"""
    return redirect(url_for('candidate_form'))

if __name__ == '__main__':
    # Get port from environment variable (Render sets PORT)
    port = int(os.environ.get('PORT', 5000))
    
    print(f"[INFO] Starting CrewAI Hiring Pipeline on port {port}")
    print(f"[INFO] CrewAI Available: {CREWAI_AVAILABLE}")
    print(f"[INFO] Environment: {os.environ.get('FLASK_ENV', 'production')}")
    
    # Run the app with proper host binding for production
    app.run(host='0.0.0.0', port=port, debug=False) 