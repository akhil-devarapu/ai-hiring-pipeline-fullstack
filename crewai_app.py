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
import random
import hashlib

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

# Question pools for unique question generation
CODING_QUESTION_POOL = [
    {"question": "Write a function to find the factorial of a number.", "expected_output": "120 (for input 5)"},
    {"question": "Write a function to check if a string is a palindrome.", "expected_output": "True (for input 'racecar')"},
    {"question": "Write a function to find the sum of all even numbers in a list.", "expected_output": "12 (for input [1,2,3,4,5,6])"},
    {"question": "Write a function to reverse a string without using built-in functions.", "expected_output": "'olleh' (for input 'hello')"},
    {"question": "Write a function to find the largest element in a list.", "expected_output": "9 (for input [3,1,4,1,5,9,2,6])"},
    {"question": "Write a function to count vowels in a string.", "expected_output": "5 (for input 'education')"},
    {"question": "Write a function to check if a number is prime.", "expected_output": "True (for input 17)"},
    {"question": "Write a function to calculate the Fibonacci sequence up to n terms.", "expected_output": "[0,1,1,2,3,5,8] (for input 7)"},
    {"question": "Write a function to remove duplicates from a list.", "expected_output": "[1,2,3,4] (for input [1,2,2,3,3,4])"},
    {"question": "Write a function to find the second largest number in a list.", "expected_output": "8 (for input [3,1,4,1,5,9,2,6,8])"}
]

TECH_QUESTION_POOL = [
    "Explain the difference between a list and a tuple in Python.",
    "What is the difference between '==' and 'is' operators in Python?",
    "Explain the concept of decorators in Python with an example.",
    "What are Python generators and how do they differ from regular functions?",
    "Explain the difference between deep copy and shallow copy in Python.",
    "What is the Global Interpreter Lock (GIL) in Python?",
    "Explain the concept of lambda functions in Python.",
    "What are Python context managers and how do you use them?",
    "Explain the difference between staticmethod and classmethod in Python.",
    "What is list comprehension and how does it differ from regular loops?"
]

HR_QUESTION_POOL = [
    "Tell me about a challenging situation you faced at work and how you handled it.",
    "Describe a time when you had to work with a difficult team member. How did you handle it?",
    "What motivates you in your professional life?",
    "How do you handle stress and pressure in the workplace?",
    "Describe a time when you had to learn a new technology quickly.",
    "Tell me about a project you're particularly proud of.",
    "How do you prioritize your work when you have multiple deadlines?",
    "Describe a time when you made a mistake at work. How did you handle it?",
    "What are your long-term career goals?",
    "How do you stay updated with the latest technology trends?"
]

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

def get_unique_question(question_type, candidate_email=None):
    """
    Get a unique question based on type and candidate history
    question_type: 'coding', 'tech', or 'hr'
    candidate_email: to track question history per candidate
    """
    if question_type == 'coding':
        pool = CODING_QUESTION_POOL
    elif question_type == 'tech':
        pool = TECH_QUESTION_POOL
    elif question_type == 'hr':
        pool = HR_QUESTION_POOL
    else:
        return None
    
    # If no email provided, return random question
    if not candidate_email:
        if question_type == 'coding':
            selected = random.choice(pool)
            return selected['question'], selected['expected_output']
        else:
            return random.choice(pool), None
    
    # Track used questions per candidate
    used_questions_key = f'used_{question_type}_questions'
    used_questions = []
    
    # Check all candidate states for this email's history
    for token, state in candidate_states.items():
        if state.get('email') == candidate_email:
            used_questions.extend(state.get(used_questions_key, []))
    
    # Remove duplicates
    used_questions = list(set(used_questions))
    
    # Filter available questions
    if question_type == 'coding':
        available_questions = [q for q in pool if q['question'] not in used_questions]
        if not available_questions:
            # Reset if all questions used
            available_questions = pool
            used_questions = []
        
        selected = random.choice(available_questions)
        return selected['question'], selected['expected_output'], used_questions + [selected['question']]
    else:
        available_questions = [q for q in pool if q not in used_questions]
        if not available_questions:
            # Reset if all questions used
            available_questions = pool
            used_questions = []
        
        selected = random.choice(available_questions)
        return selected, None, used_questions + [selected]

def generate_question_with_ai_fallback(question_type, candidate_state=None):
    """
    Generate a question using AI with fallback to question pool
    """
    candidate_email = candidate_state.get('email') if candidate_state else None
    
    # Try to get unique question from pool first
    if question_type == 'coding':
        question, expected_output, updated_used = get_unique_question('coding', candidate_email)
        if candidate_state and candidate_email:
            candidate_state['used_coding_questions'] = updated_used
        return question, expected_output
    elif question_type == 'tech':
        question, _, updated_used = get_unique_question('tech', candidate_email)
        if candidate_state and candidate_email:
            candidate_state['used_tech_questions'] = updated_used
        return question
    elif question_type == 'hr':
        question, _, updated_used = get_unique_question('hr', candidate_email)
        if candidate_state and candidate_email:
            candidate_state['used_hr_questions'] = updated_used
        return question
    
    # Fallback to AI generation only if pool is exhausted or unavailable
    if CREWAI_AVAILABLE and question_type == 'coding':
        try:
            # AI generation logic here (existing code)
            pass
        except:
            pass
    
    # Final fallback
    if question_type == 'coding':
        return "Write a function to add two numbers and return the result.", "5 (for input 2, 3)"
    elif question_type == 'tech':
        return "Explain the difference between a list and a tuple in Python."
    else:
        return "Tell me about a challenging situation you faced at work and how you handled it."

def analyze_code_quality(code, question, language='python'):
    """
    Analyze code quality with detailed scoring
    """
    score = 0
    feedback_parts = []
    
    # Basic syntax and structure checks (40 points)
    if language.lower() == 'python':
        # Check for function definition
        if 'def ' in code:
            score += 15
            feedback_parts.append("✓ Function definition found")
        else:
            feedback_parts.append("✗ No function definition found")
        
        # Check for return statement
        if 'return' in code:
            score += 10
            feedback_parts.append("✓ Return statement present")
        else:
            feedback_parts.append("✗ Missing return statement")
        
        # Check for proper indentation (basic check)
        lines = code.split('\n')
        indented_lines = [line for line in lines if line.startswith('    ') or line.startswith('\t')]
        if indented_lines:
            score += 5
            feedback_parts.append("✓ Proper indentation detected")
        
        # Check for comments or documentation
        if '#' in code or '"""' in code or "'''" in code:
            score += 5
            feedback_parts.append("✓ Code documentation found")
        
        # Check for error handling
        if 'try:' in code or 'except' in code:
            score += 5
            feedback_parts.append("✓ Error handling implemented")
    
    # Code complexity and logic (30 points)
    code_length = len(code.strip())
    if code_length > 50:
        score += 10
        feedback_parts.append("✓ Adequate code length")
    
    # Check for loops or conditionals
    if any(keyword in code for keyword in ['for ', 'while ', 'if ']):
        score += 10
        feedback_parts.append("✓ Control structures used")
    
    # Check for built-in functions usage
    if any(func in code for func in ['len(', 'sum(', 'max(', 'min(', 'sorted(']):
        score += 5
        feedback_parts.append("✓ Built-in functions utilized")
    
    # Variable naming (10 points)
    import re
    variables = re.findall(r'\b[a-z_][a-z0-9_]*\b', code.lower())
    meaningful_vars = [var for var in variables if len(var) > 2 and var not in ['def', 'for', 'if', 'try']]
    if meaningful_vars:
        score += 10
        feedback_parts.append("✓ Meaningful variable names used")
    
    # Question-specific checks (20 points)
    question_lower = question.lower()
    code_lower = code.lower()
    
    if 'factorial' in question_lower:
        if any(keyword in code_lower for keyword in ['factorial', '!']):
            score += 15
        if 'math.factorial' in code_lower:
            score += 5
            feedback_parts.append("✓ Uses appropriate library function")
    elif 'palindrome' in question_lower:
        if any(keyword in code_lower for keyword in ['reverse', '[::-1]', 'reversed']):
            score += 15
            feedback_parts.append("✓ Palindrome logic implemented")
    elif 'even' in question_lower:
        if '%' in code or 'mod' in code_lower:
            score += 15
            feedback_parts.append("✓ Modulo operation for even numbers")
    elif 'sum' in question_lower:
        if 'sum(' in code_lower:
            score += 10
            feedback_parts.append("✓ Sum function used appropriately")
    elif 'largest' in question_lower or 'maximum' in question_lower:
        if 'max(' in code_lower:
            score += 10
            feedback_parts.append("✓ Max function used")
    elif 'prime' in question_lower:
        if any(keyword in code_lower for keyword in ['%', 'mod', 'sqrt']):
            score += 15
            feedback_parts.append("✓ Prime number logic implemented")
    
    # Ensure score doesn't exceed 100
    score = min(score, 100)
    
    # Generate recommendation
    if score >= 80:
        recommendation = "PASS"
        feedback_parts.append(f"\n🎉 Excellent work! Score: {score}/100")
    elif score >= 60:
        recommendation = "PASS"
        feedback_parts.append(f"\n✅ Good effort! Score: {score}/100")
    else:
        recommendation = "FAIL"
        feedback_parts.append(f"\n❌ Needs improvement. Score: {score}/100")
    
    feedback = "\n".join(feedback_parts)
    
    return {
        'score': score,
        'feedback': feedback,
        'recommendation': recommendation
    }

def analyze_technical_answer(answer, question):
    """
    Analyze technical interview answer quality
    """
    score = 0
    feedback_parts = []
    
    # Basic answer quality (30 points)
    answer_length = len(answer.strip())
    if answer_length > 100:
        score += 15
        feedback_parts.append("✓ Comprehensive answer length")
    elif answer_length > 50:
        score += 10
        feedback_parts.append("✓ Adequate answer length")
    else:
        feedback_parts.append("✗ Answer too brief")
    
    # Technical terms and concepts (40 points)
    question_lower = question.lower()
    answer_lower = answer.lower()
    
    if 'list' in question_lower and 'tuple' in question_lower:
        technical_terms = ['mutable', 'immutable', 'ordered', 'changeable', 'brackets', 'parentheses']
        found_terms = [term for term in technical_terms if term in answer_lower]
        score += min(len(found_terms) * 5, 25)
        if found_terms:
            feedback_parts.append(f"✓ Technical terms used: {', '.join(found_terms)}")
    elif 'decorator' in question_lower:
        technical_terms = ['function', 'wrapper', '@', 'higher-order', 'modify', 'enhance']
        found_terms = [term for term in technical_terms if term in answer_lower]
        score += min(len(found_terms) * 5, 25)
    elif 'generator' in question_lower:
        technical_terms = ['yield', 'iterator', 'memory', 'lazy', 'next()']
        found_terms = [term for term in technical_terms if term in answer_lower]
        score += min(len(found_terms) * 5, 25)
    
    # Examples and practical application (20 points)
    if any(keyword in answer_lower for keyword in ['example', 'for instance', 'such as', 'like']):
        score += 10
        feedback_parts.append("✓ Examples provided")
    
    if any(keyword in answer for keyword in ['def ', 'class ', 'import ', '>>>']):
        score += 10
        feedback_parts.append("✓ Code examples included")
    
    # Clarity and structure (10 points)
    sentences = answer.split('.')
    if len(sentences) > 2:
        score += 5
        feedback_parts.append("✓ Well-structured answer")
    
    if any(keyword in answer_lower for keyword in ['first', 'second', 'however', 'while', 'whereas']):
        score += 5
        feedback_parts.append("✓ Clear comparison and contrast")
    
    # Ensure score doesn't exceed 100
    score = min(score, 100)
    
    # Generate recommendation
    if score >= 80:
        recommendation = "PASS"
        feedback_parts.append(f"\n🎉 Excellent technical knowledge! Score: {score}/100")
    elif score >= 60:
        recommendation = "PASS"
        feedback_parts.append(f"\n✅ Good technical understanding! Score: {score}/100")
    else:
        recommendation = "FAIL"
        feedback_parts.append(f"\n❌ Technical knowledge needs improvement. Score: {score}/100")
    
    feedback = "\n".join(feedback_parts)
    
    return {
        'score': score,
        'feedback': feedback,
        'recommendation': recommendation
    }

def analyze_hr_answer(answer, question):
    """
    Analyze HR interview answer quality
    """
    score = 0
    feedback_parts = []
    
    # Answer completeness (25 points)
    answer_length = len(answer.strip())
    if answer_length > 150:
        score += 20
        feedback_parts.append("✓ Comprehensive and detailed answer")
    elif answer_length > 75:
        score += 15
        feedback_parts.append("✓ Good answer length")
    elif answer_length > 30:
        score += 10
        feedback_parts.append("✓ Adequate answer length")
    else:
        feedback_parts.append("✗ Answer too brief")
    
    # Professional vocabulary and tone (20 points)
    professional_terms = ['professional', 'team', 'collaboration', 'responsibility', 'challenge', 
                         'solution', 'experience', 'learned', 'improved', 'achieved']
    found_terms = [term for term in professional_terms if term.lower() in answer.lower()]
    score += min(len(found_terms) * 2, 15)
    if found_terms:
        feedback_parts.append(f"✓ Professional vocabulary: {len(found_terms)} terms used")
    
    # Structure and storytelling (25 points)
    answer_lower = answer.lower()
    
    # STAR method indicators
    star_elements = {
        'situation': any(keyword in answer_lower for keyword in ['situation', 'when', 'time', 'during']),
        'task': any(keyword in answer_lower for keyword in ['task', 'responsibility', 'role', 'needed to']),
        'action': any(keyword in answer_lower for keyword in ['action', 'did', 'took', 'implemented', 'decided']),
        'result': any(keyword in answer_lower for keyword in ['result', 'outcome', 'achieved', 'learned', 'improved'])
    }
    
    star_score = sum(star_elements.values()) * 5
    score += star_score
    if star_score > 0:
        feedback_parts.append(f"✓ STAR method elements: {star_score/5:.0f}/4 components")
    
    # Problem-solving and learning (20 points)
    if any(keyword in answer_lower for keyword in ['problem', 'challenge', 'difficult', 'issue']):
        score += 8
        feedback_parts.append("✓ Acknowledges challenges")
    
    if any(keyword in answer_lower for keyword in ['solved', 'resolved', 'handled', 'managed', 'overcame']):
        score += 7
        feedback_parts.append("✓ Shows problem-solving skills")
    
    if any(keyword in answer_lower for keyword in ['learned', 'growth', 'improved', 'better', 'experience']):
        score += 5
        feedback_parts.append("✓ Demonstrates learning and growth")
    
    # Communication and interpersonal skills (10 points)
    if any(keyword in answer_lower for keyword in ['team', 'communication', 'discussed', 'collaborated']):
        score += 5
        feedback_parts.append("✓ Mentions teamwork/communication")
    
    if any(keyword in answer_lower for keyword in ['feedback', 'listen', 'understand', 'empathy']):
        score += 5
        feedback_parts.append("✓ Shows interpersonal awareness")
    
    # Ensure score doesn't exceed 100
    score = min(score, 100)
    
    # Generate recommendation
    if score >= 80:
        recommendation = "PASS"
        feedback_parts.append(f"\n🎉 Excellent communication and professionalism! Score: {score}/100")
    elif score >= 60:
        recommendation = "PASS"
        feedback_parts.append(f"\n✅ Good professional response! Score: {score}/100")
    else:
        recommendation = "FAIL"
        feedback_parts.append(f"\n❌ Professional communication needs improvement. Score: {score}/100")
    
    feedback = "\n".join(feedback_parts)
    
    return {
        'score': score,
        'feedback': feedback,
        'recommendation': recommendation
    }

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
            # Generate unique coding question
            candidate_state_temp = {'email': email}
            question, expected_output = generate_question_with_ai_fallback('coding', candidate_state_temp)
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
                'hr_interview_completed': False,
                'used_coding_questions': [question] if question else [],
                'used_tech_questions': [],
                'used_hr_questions': []
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
        # Generate a unique question for this candidate
        question, expected_output = generate_question_with_ai_fallback('coding', state)
        state['question'] = question
        state['expected_output'] = expected_output
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
        
        # Use improved code analysis with AI fallback
        try:
            # First, use our improved analysis system
            analysis_result = analyze_code_quality(code, question, language)
            score = analysis_result['score']
            recommendation = analysis_result['recommendation']
            feedback = analysis_result['feedback']
            
            # If score is borderline, try to get AI enhancement (optional)
            if CREWAI_AVAILABLE and 60 <= score <= 85:
                try:
                    evaluation_task = Task(
                        description=f"""
                        Review this coding solution analysis and provide additional insights:
                        
                        Question: {question}
                        Code: {code}
                        Current Score: {score}
                        Current Feedback: {feedback}
                        
                        Provide additional feedback on:
                        1. Code efficiency and optimization
                        2. Edge case handling
                        3. Best practices adherence
                        4. Suggestions for improvement
                        
                        Return a brief enhancement to the existing feedback.
                        """,
                        agent=create_coding_assessment_agent(),
                        expected_output="Additional feedback and insights"
                    )
                    
                    evaluation_crew = Crew(
                        agents=[create_coding_assessment_agent()],
                        tasks=[evaluation_task],
                        verbose=True,
                        process=Process.sequential
                    )
                    
                    ai_enhancement = evaluation_crew.kickoff()
                    feedback += f"\n\nAI Enhancement: {ai_enhancement}"
                    print(f"[INFO] AI enhancement added to analysis")
                except Exception as e:
                    print(f"[INFO] AI enhancement failed, using base analysis: {e}")
            
        except Exception as e:
            print(f"[ERROR] Error in code analysis: {e}")
            # Ultimate fallback
            score = 50
            recommendation = "FAIL"
            feedback = f"Error during code analysis: {str(e)}. Please review code manually."
        
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
        # Generate a unique technical question for this candidate
        question = generate_question_with_ai_fallback('tech', state)
        state['tech_question'] = question
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    else:
        question = state['tech_question']
    
    if request.method == 'POST':
        answer = request.form['answer']
        
        # Use improved technical analysis
        try:
            analysis_result = analyze_technical_answer(answer, question)
            score = analysis_result['score']
            recommendation = analysis_result['recommendation']
            feedback = analysis_result['feedback']
            
            print(f"[INFO] Technical analysis completed. Score: {score}")
            
        except Exception as e:
            print(f"[ERROR] Error in technical analysis: {e}")
            # Ultimate fallback
            score = 50
            recommendation = "FAIL"
            feedback = f"Error during technical analysis: {str(e)}. Please review answer manually."
        
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
        # Generate a unique HR question for this candidate
        question = generate_question_with_ai_fallback('hr', state)
        state['hr_question'] = question
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    else:
        question = state['hr_question']
    
    if request.method == 'POST':
        answer = request.form['answer']
        
        # Use improved HR analysis
        try:
            analysis_result = analyze_hr_answer(answer, question)
            score = analysis_result['score']
            recommendation = analysis_result['recommendation']
            feedback = analysis_result['feedback']
            
            print(f"[INFO] HR analysis completed. Score: {score}")
            
        except Exception as e:
            print(f"[ERROR] Error in HR analysis: {e}")
            # Ultimate fallback
            score = 50
            recommendation = "FAIL"
            feedback = f"Error during HR analysis: {str(e)}. Please review answer manually."
        
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