from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message
import os
import json
from dotenv import load_dotenv
load_dotenv()

from utils.resume_parser import parse_resume
from utils.email_utils import send_email
from utils.judge0_utils import submit_code, get_result
import uuid
import tempfile
import openai
from datetime import datetime

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

JD = "We are looking for a Python developer ."

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
        # If file is corrupted, try to backup and start fresh
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
        # Create backup before saving
        if os.path.exists(CANDIDATE_STATES_FILE):
            backup_file = f"{CANDIDATE_STATES_FILE}.backup"
            os.rename(CANDIDATE_STATES_FILE, backup_file)
        
        with open(CANDIDATE_STATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(states, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(states)} candidate states to file")
    except Exception as e:
        print(f"Error saving candidate states: {e}")
        # Try to restore from backup
        try:
            backup_file = f"{CANDIDATE_STATES_FILE}.backup"
            if os.path.exists(backup_file):
                os.rename(backup_file, CANDIDATE_STATES_FILE)
                print("Restored from backup file")
        except:
            pass

# Load existing states
candidate_states = load_candidate_states()

# Add a simple in-memory fallback for development
if not candidate_states:
    print("No candidate states loaded from file, starting with empty state")
    candidate_states = {}

# Ensure the file exists with empty state if it doesn't exist
if not os.path.exists(CANDIDATE_STATES_FILE):
    print(f"Creating new candidate states file: {CANDIDATE_STATES_FILE}")
    save_candidate_states(candidate_states)

def generate_offer_letter_html(candidate_name, candidate_email):
    """
    Generate offer letter as HTML instead of PDF to avoid external dependencies
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Offer Letter</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
            .content {{ line-height: 1.6; }}
            .signature {{ margin-top: 40px; }}
            .footer {{ margin-top: 40px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎉 OFFER LETTER</h1>
            <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <div class="content">
            <p>Dear <strong>{candidate_name}</strong>,</p>
            
            <p>We are delighted to offer you a position at our company! After successfully completing all stages of our comprehensive hiring process, including:</p>
            
            <ul>
                <li>✅ Initial application screening</li>
                <li>✅ Coding assessment with AI evaluation</li>
                <li>✅ Technical interview with detailed analysis</li>
                <li>✅ HR interview with cultural fit assessment</li>
            </ul>
            
            <p>You have demonstrated exceptional skills, knowledge, and professionalism throughout the entire process.</p>
            
            <p><strong>Position:</strong> Python Developer</p>
            <p><strong>Start Date:</strong> To be discussed</p>
            <p><strong>Location:</strong> Remote/Hybrid</p>
            
            <p>We are excited to have you join our team and contribute to our mission of building innovative solutions.</p>
            
            <p>Please contact us at <strong>{candidate_email}</strong> to discuss the next steps and any questions you may have.</p>
        </div>
        
        <div class="signature">
            <p>Sincerely,<br>
            <strong>Hiring Team</strong><br>
            <em>AI-Powered Hiring Pipeline</em></p>
        </div>
        
        <div class="footer">
            <p>This offer letter was automatically generated by our AI-powered hiring system.</p>
        </div>
    </body>
    </html>
    """
    return html

def analyze_coding_solution(question, code, output, language):
    """
    Analyze the coding solution using AI with detailed evaluation
    Returns a score between 0-100 and detailed feedback
    """
    prompt = f"""
    Analyze this coding solution comprehensively:

    Question: {question}
    Programming Language: {language}
    Candidate's Code:
    {code}
    
    Code Output: {output}

    Please evaluate the solution on the following criteria (0-100 points each):
    1. Correctness (Does the code solve the problem correctly?)
    2. Code Quality (Is the code well-structured, readable, and follows best practices?)
    3. Efficiency (Is the solution efficient in terms of time and space complexity?)
    4. Edge Case Handling (Does the code handle edge cases properly?)
    5. Documentation (Is the code properly commented and documented?)

    Provide:
    1. Overall score (0-100)
    2. Detailed feedback for each criterion
    3. Specific suggestions for improvement
    4. Final recommendation: PASS (if score >= 80) or FAIL (if score < 80)

    Format your response as:
    Score: [number]
    Feedback: [detailed feedback]
    Recommendation: [PASS/FAIL]
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content.strip()
    
    # Extract score and recommendation
    score = 0
    recommendation = "FAIL"
    
    try:
        if "Score:" in result:
            score_line = [line for line in result.split('\n') if line.strip().startswith('Score:')][0]
            score = int(score_line.split(':')[1].strip())
        
        if "Recommendation:" in result:
            rec_line = [line for line in result.split('\n') if line.strip().startswith('Recommendation:')][0]
            recommendation = rec_line.split(':')[1].strip()
    except:
        pass
    
    return {
        'score': score,
        'feedback': result,
        'recommendation': recommendation
    }

def analyze_technical_answer(question, answer):
    """
    Analyze the technical interview answer using AI with 80% threshold
    Returns a score between 0-100 and detailed feedback
    """
    prompt = f"""
    Analyze this technical interview answer comprehensively:

    Question: {question}
    Candidate's Answer: {answer}

    Please evaluate the answer on the following criteria (0-100 points each):
    1. Accuracy (Is the technical information correct?)
    2. Completeness (Does the answer cover all aspects of the question?)
    3. Depth of Knowledge (Does the candidate demonstrate deep understanding?)
    4. Clarity (Is the explanation clear and well-structured?)
    5. Practical Application (Does the candidate show practical understanding?)

    Provide:
    1. Overall score (0-100)
    2. Detailed feedback for each criterion
    3. Specific suggestions for improvement
    4. Final recommendation: PASS (if score >= 80) or FAIL (if score < 80)

    Format your response as:
    Score: [number]
    Feedback: [detailed feedback]
    Recommendation: [PASS/FAIL]
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content.strip()
    
    # Extract score and recommendation
    score = 0
    recommendation = "FAIL"
    
    try:
        if "Score:" in result:
            score_line = [line for line in result.split('\n') if line.strip().startswith('Score:')][0]
            score = int(score_line.split(':')[1].strip())
        
        if "Recommendation:" in result:
            rec_line = [line for line in result.split('\n') if line.strip().startswith('Recommendation:')][0]
            recommendation = rec_line.split(':')[1].strip()
    except:
        pass
    
    return {
        'score': score,
        'feedback': result,
        'recommendation': recommendation
    }

def analyze_hr_answer(question, answer):
    """
    Analyze the HR interview answer using AI with 80% threshold
    Returns a score between 0-100 and detailed feedback
    """
    prompt = f"""
    Analyze this HR interview answer comprehensively:

    Question: {question}
    Candidate's Answer: {answer}

    Please evaluate the answer on the following criteria (0-100 points each):
    1. Relevance (Does the answer directly address the question?)
    2. Professionalism (Is the response professional and appropriate?)
    3. Clarity (Is the explanation clear and well-structured?)
    4. Honesty (Does the candidate appear genuine and honest?)
    5. Cultural Fit (Does the answer align with workplace values?)

    Provide:
    1. Overall score (0-100)
    2. Detailed feedback for each criterion
    3. Specific suggestions for improvement
    4. Final recommendation: PASS (if score >= 80) or FAIL (if score < 80)

    Format your response as:
    Score: [number]
    Feedback: [detailed feedback]
    Recommendation: [PASS/FAIL]
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content.strip()
    
    # Extract score and recommendation
    score = 0
    recommendation = "FAIL"
    
    try:
        if "Score:" in result:
            score_line = [line for line in result.split('\n') if line.strip().startswith('Score:')][0]
            score = int(score_line.split(':')[1].strip())
        
        if "Recommendation:" in result:
            rec_line = [line for line in result.split('\n') if line.strip().startswith('Recommendation:')][0]
            recommendation = rec_line.split(':')[1].strip()
    except:
        pass
    
    return {
        'score': score,
        'feedback': result,
        'recommendation': recommendation
    }

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
        # Use OpenAI to compare resume+skills to JD
        prompt = f"Job Description: {JD}\n\nCandidate Resume: {resume_text}\n\nCandidate Skills: {skills}\n\nDoes this candidate match the job description? Reply Yes or No and explain."
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        match_result = response.choices[0].message.content.strip()
        if match_result.lower().startswith('yes'):
            # Generate a new token for this candidate
            token = str(uuid.uuid4())
            candidate_states[token] = {
                'name': name,
                'email': email,
                'resume_text': resume_text,
                'skills': skills
            }
            save_candidate_states(candidate_states)
            coding_link = url_for('coding_test', token=token, _external=True)
            send_email(
                subject='Coding Assessment Link',
                recipients=[email],
                body=f"Hi {name},\n\nYou have been shortlisted! Please take your coding test here: {coding_link}\n\nBest,\nHiring Team",
                mail=mail
            )
            flash('You have been shortlisted! Check your email for the coding test link.', 'success')
        else:
            send_email(
                subject='Application Update',
                recipients=[email],
                body=f"Hi {name},\n\nThank you for applying. Unfortunately, you do not match our requirements at this time.\n\nBest,\nHiring Team",
                mail=mail
            )
            flash('Thank you for applying. You will receive an update by email.', 'info')
        return redirect(url_for('candidate_form'))
    return render_template('form.html')

@app.route('/coding-test/<token>', methods=['GET', 'POST'])
def coding_test(token):
    print(f"Accessing coding test with token: {token}")
    print(f"Available tokens: {list(candidate_states.keys())}")
    
    state = candidate_states.get(token)
    if not state:
        print(f"Token {token} not found in candidate states")
        return render_template('error.html', 
                             message="Invalid or expired coding test link.",
                             suggestion="Please check your email for the correct link or contact support.")
    
    print(f"Found state for token {token}: {state.get('name', 'Unknown')}")
    
    # Ensure question and expected_output exist
    question = state.get('question')
    expected_output = state.get('expected_output')
    if not question or not expected_output:
        unique_id = str(uuid.uuid4())
        prompt = (
            f"Generate a unique, never-repeated, easy-level coding question for interviews. "
            f"Include the question and the expected output for input: 2 3. "
            f"Format: Question: ...\nExpected Output: ...\n"
            f"Randomizer: {unique_id}"
        )
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()
        if 'Expected Output:' in content:
            question, expected = content.split('Expected Output:')
            question = question.replace('Question:', '').strip()
            expected_output = expected.strip()
        else:
            question = content
            expected_output = "5"  # fallback
        state['question'] = question
        state['expected_output'] = expected_output
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    
    if request.method == 'POST':
        code = request.form['code']
        language = request.form['language']
        
        # Submit code and get output
        submission_token = submit_code(code, language, stdin="2 3\n")
        output = get_result(submission_token)
        
        # Analyze the coding solution using AI
        analysis_result = analyze_coding_solution(question, code, output, language)
        
        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        
        # Store analysis results in state
        state['coding_analysis'] = analysis_result
        candidate_states[token] = state
        save_candidate_states(candidate_states)
        
        if analysis_result['recommendation'] == 'PASS':
            tech_link = url_for('tech_interview', token=token, _external=True)
            send_email(
                subject='Technical Interview Link',
                recipients=[email],
                body=f"Hi {name},\n\nCongratulations! You passed the coding test with a score of {analysis_result['score']}/100. Attend your technical interview here: {tech_link}\n\nBest,\nHiring Team",
                mail=mail
            )
            return render_template('coding_result.html', 
                                passed=True, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'],
                                next_stage="Technical Interview")
        else:
            send_email(
                subject='Application Update',
                recipients=[email],
                body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not pass the coding test. Your score was {analysis_result['score']}/100.\n\nBest,\nHiring Team",
                mail=mail
            )
            return render_template('coding_result.html', 
                                passed=False, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'])
    
    return render_template('coding_test.html', question=question)

@app.route('/tech-interview/<token>', methods=['GET', 'POST'])
def tech_interview(token):
    print(f"Accessing tech interview with token: {token}")
    print(f"Available tokens: {list(candidate_states.keys())}")
    
    state = candidate_states.get(token)
    if not state:
        print(f"Token {token} not found in candidate states")
        return render_template('error.html', 
                             message="Invalid or expired technical interview link.",
                             suggestion="Please check your email for the correct link or contact support.")
    
    print(f"Found state for token {token}: {state.get('name', 'Unknown')}")

    if 'tech_question' not in state:
        resume_text = state.get('resume_text', '')
        prompt = f"Job Description: {JD}\n\nCandidate Resume: {resume_text}\n\nGenerate a technical interview question for this candidate."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        question = response.choices[0].message.content.strip()
        state['tech_question'] = question
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    else:
        question = state['tech_question']

    if request.method == 'POST':
        answer = request.form['answer']
        
        # Analyze the technical answer using AI
        analysis_result = analyze_technical_answer(question, answer)
        
        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        
        # Store analysis results in state
        state['tech_analysis'] = analysis_result
        candidate_states[token] = state
        save_candidate_states(candidate_states)
        
        if analysis_result['recommendation'] == 'PASS':
            hr_link = url_for('hr_interview', token=token, _external=True)
            send_email(
                subject='HR Interview Link',
                recipients=[email],
                body=f"Hi {name},\n\nCongratulations! You passed the technical interview with a score of {analysis_result['score']}/100. Attend your HR interview here: {hr_link}\n\nBest,\nHiring Team",
                mail=mail
            )
            return render_template('tech_result.html', 
                                passed=True, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'],
                                next_stage="HR Interview")
        else:
            send_email(
                subject='Application Update',
                recipients=[email],
                body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not pass the technical interview. Your score was {analysis_result['score']}/100.\n\nBest,\nHiring Team",
                mail=mail
            )
            return render_template('tech_result.html', 
                                passed=False, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'])
    
    return render_template('tech_interview.html', question=question)

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
    
    html_content = generate_offer_letter_html(name, email)
    return html_content

@app.route('/hr-interview/<token>', methods=['GET', 'POST'])
def hr_interview(token):
    print(f"Accessing HR interview with token: {token}")
    print(f"Available tokens: {list(candidate_states.keys())}")
    
    state = candidate_states.get(token)
    if not state:
        print(f"Token {token} not found in candidate states")
        return render_template('error.html', 
                             message="Invalid or expired HR interview link.",
                             suggestion="Please check your email for the correct link or contact support.")
    
    print(f"Found state for token {token}: {state.get('name', 'Unknown')}")

    if 'hr_question' not in state:
        prompt = "Generate a basic HR interview question for a job candidate."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        question = response.choices[0].message.content.strip()
        state['hr_question'] = question
        candidate_states[token] = state
        save_candidate_states(candidate_states)
    else:
        question = state['hr_question']

    if request.method == 'POST':
        answer = request.form['answer']
        
        # Analyze the HR answer using AI
        analysis_result = analyze_hr_answer(question, answer)
        
        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        
        # Store analysis results in state
        state['hr_analysis'] = analysis_result
        candidate_states[token] = state
        save_candidate_states(candidate_states)
        
        if analysis_result['recommendation'] == 'PASS':
            try:
                html_content = generate_offer_letter_html(name, email)
                msg = Message(
                    subject='🎉 Congratulations! Your Offer Letter',
                    recipients=[email],
                    body=f"Hi {name},\n\nCongratulations! You have cleared all rounds with a score of {analysis_result['score']}/100. Please find your offer letter in the email body.\n\nBest,\nHiring Team",
                    html=html_content
                )
                mail.send(msg)
                
                # Add offer letter link to the result
                offer_link = url_for('view_offer_letter', token=token, _external=True)
                return render_template('hr_result.html', 
                                    passed=True, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'],
                                    offer_link=offer_link)
            except Exception as e:
                # If email fails, still show success but with a note
                offer_link = url_for('view_offer_letter', token=token, _external=True)
                return render_template('hr_result.html', 
                                    passed=True, 
                                    score=analysis_result['score'],
                                    feedback=analysis_result['feedback'],
                                    offer_link=offer_link,
                                    email_error=True)
        else:
            try:
                send_email(
                    subject='Application Update',
                    recipients=[email],
                    body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not clear the HR interview. Your score was {analysis_result['score']}/100.\n\nBest,\nHiring Team",
                    mail=mail
                )
            except Exception as e:
                pass  # Continue even if email fails
            
            return render_template('hr_result.html', 
                                passed=False, 
                                score=analysis_result['score'],
                                feedback=analysis_result['feedback'])
    
    return render_template('hr_interview.html', question=question)

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
        'states': {k: {'name': v.get('name', 'Unknown'), 'email': v.get('email', 'Unknown')} 
                  for k, v in candidate_states.items()}
    }

@app.route('/')
def index():
    """Redirect to the application form"""
    return redirect(url_for('candidate_form'))

if __name__ == '__main__':
    # Get port from environment variable (Render sets PORT)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app with proper host binding for production
    app.run(host='0.0.0.0', port=port, debug=False)

    # Get port from environment variable (Render sets PORT)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app with proper host binding for production
    app.run(host='0.0.0.0', port=port, debug=False)
