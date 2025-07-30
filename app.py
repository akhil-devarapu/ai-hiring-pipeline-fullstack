from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
load_dotenv()

from utils.resume_parser import parse_resume
from utils.email_utils import send_email
from utils.judge0_utils import submit_code, get_result
import uuid
import pdfkit
import tempfile
from openai import OpenAI

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
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

JD = "We are looking for a Python developer ."
candidate_states = {}

def generate_offer_letter_pdf(candidate_name, candidate_email):
    html = f"""
    <html><body>
    <h2>Offer Letter</h2>
    <p>Dear {candidate_name},</p>
    <p>Congratulations! We are pleased to offer you a position at our company.</p>
    <p>Please contact us at {candidate_email} if you have any questions.</p>
    <p>Sincerely,<br>Hiring Team</p>
    </body></html>
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        pdfkit.from_string(html, tmp.name)
        return tmp.name

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
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
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
    state = candidate_states.get(token)
    if not state:
        return "Invalid or expired coding test link."
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
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
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
    if request.method == 'POST':
        code = request.form['code']
        language = request.form['language']
        submission_token = submit_code(code, language, stdin="2 3\n")
        output = get_result(submission_token)
        eval_prompt = f"The expected output is:\n{expected_output}\nThe candidate's code output is:\n{output}\nIs the output at least 90% correct? Reply only with 'Yes' or 'No'."
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        eval_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}]
        )
        evaluation = eval_response.choices[0].message.content.strip()
        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        if 'yes' in evaluation.lower():
            tech_link = url_for('tech_interview', token='dummy', _external=True)
            send_email(
                subject='Technical Interview Link',
                recipients=[email],
                body=f"Hi {name},\n\nYou passed the coding test! Attend your technical interview here: {tech_link}\n\nBest,\nHiring Team",
                mail=mail
            )
            return "You passed! Check your email for the next stage."
        else:
            send_email(
                subject='Application Update',
                recipients=[email],
                body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not pass the coding test.\n\nBest,\nHiring Team",
                mail=mail
            )
            return "Thank you for participating. You will receive an update by email."
    return render_template('coding_test.html', question=question)

@app.route('/tech-interview/<token>', methods=['GET', 'POST'])
def tech_interview(token):
    state = candidate_states.get(token)
    if not state:
        return "Invalid or expired link."

    if 'tech_question' not in state:
        resume_text = state.get('resume_text', '')
        prompt = f"Job Description: {JD}\n\nCandidate Resume: {resume_text}\n\nGenerate a technical interview question for this candidate."
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        question = response.choices[0].message.content.strip()
        state['tech_question'] = question
        candidate_states[token] = state
    else:
        question = state['tech_question']

    if request.method == 'POST':
        answer = request.form['answer']
        eval_prompt = f"Technical interview question: {question}\nCandidate's answer: {answer}\nIs the answer correct and detailed? Reply Yes or No and explain."
        eval_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}]
        )
        evaluation = eval_response.choices[0].message.content.strip()

        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        if evaluation.lower().startswith('yes'):
            hr_link = url_for('hr_interview', token=token, _external=True)
            send_email(
                subject='HR Interview Link',
                recipients=[email],
                body=f"Hi {name},\n\nYou passed the technical interview! Attend your HR interview here: {hr_link}\n\nBest,\nHiring Team",
                mail=mail
            )
            return "You passed! Check your email for the next stage."
        else:
            send_email(
                subject='Application Update',
                recipients=[email],
                body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not pass the technical interview.\n\nBest,\nHiring Team",
                mail=mail
            )
            return "Thank you for participating. You will receive an update by email."
    return render_template('tech_interview.html', question=question)

@app.route('/hr-interview/<token>', methods=['GET', 'POST'])
def hr_interview(token):
    state = candidate_states.get(token)
    if not state:
        return "Invalid or expired link."

    if 'hr_question' not in state:
        prompt = "Generate a basic HR interview question for a job candidate."
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        question = response.choices[0].message.content.strip()
        state['hr_question'] = question
        candidate_states[token] = state
    else:
        question = state['hr_question']

    if request.method == 'POST':
        answer = request.form['answer']
        eval_prompt = f"HR interview question: {question}\nCandidate's answer: {answer}\nIs the answer appropriate and well-explained? Reply Yes or No and explain."
        eval_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}]
        )
        evaluation = eval_response.choices[0].message.content.strip()

        email = state.get('email', 'candidate@example.com')
        name = state.get('name', 'Candidate')
        if evaluation.lower().startswith('yes'):
            pdf_path = generate_offer_letter_pdf(name, email)
            msg = Message(
                subject='Offer Letter',
                recipients=[email],
                body=f"Hi {name},\n\nCongratulations! You have cleared all rounds. Please find your offer letter attached.\n\nBest,\nHiring Team"
            )
            with open(pdf_path, 'rb') as f:
                msg.attach('OfferLetter.pdf', 'application/pdf', f.read())
            mail.send(msg)
            os.remove(pdf_path)
            return "Congratulations! You have cleared all rounds. Check your email for the offer letter."
        else:
            send_email(
                subject='Application Update',
                recipients=[email],
                body=f"Hi {name},\n\nThank you for participating. Unfortunately, you did not clear the HR interview.\n\nBest,\nHiring Team",
                mail=mail
            )
            return "Thank you for participating. You will receive an update by email."
    return render_template('hr_interview.html', question=question)

if __name__ == '__main__':
    app.run(debug=True)
