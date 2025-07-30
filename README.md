# NxtWave Automated Hiring Pipeline

A fully automated, web-based hiring pipeline for NxtWave SDI/SDM (Instructor/Mentor) roles. Handles candidate intake, skill matching, coding assessment, technical and HR interviews, and automated offer letter generation and delivery.

## Features
- Candidate intake form with resume upload
- Skill matching and automated email notifications
- Web-based coding assessment with auto-grading
- Technical and HR interview stages (web Q&A, auto-grading)
- Automated offer letter PDF generation and email delivery
- Candidate status tracking in database
- Modular and extensible (add more stages, questions, or admin dashboard)

## Tech Stack
- Python, Flask, Flask-Mail, Flask-SQLAlchemy
- Bootstrap (for UI)
- pdfkit + wkhtmltopdf (for PDF generation)
- SQLite (default, easy to switch to Postgres/MySQL)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install wkhtmltopdf (for PDF generation)
- Download from: https://wkhtmltopdf.org/downloads.html
- Make sure `wkhtmltopdf` is in your system PATH, or set the path in your code if needed.

### 4. Set Environment Variables
Create a `.env` file in the project root with:
```
SECRET_KEY=your_secret_key
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_password_or_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
DATABASE_URL=sqlite:///db.sqlite3
```

### 5. Run the App
```bash
python app.py
```
Visit [http://localhost:5000/form](http://localhost:5000/form) to start the pipeline.

## How the Pipeline Works
1. **Candidate fills out the form** and uploads resume.
2. **Skill matching**: If suitable, receives coding test link by email; else, rejection email.
3. **Coding assessment**: Candidate submits code; if passed, receives tech interview link; else, rejection.
4. **Technical interview**: Candidate answers a question; if passed, receives HR interview link; else, rejection.
5. **HR interview**: Candidate answers a question; if passed, receives offer letter PDF by email; else, rejection.

## Email Setup
- Uses Flask-Mail with SMTP (Gmail recommended for testing).
- For Gmail, you may need to use an App Password if 2FA is enabled.

## PDF Offer Letter
- Uses `pdfkit` and `wkhtmltopdf` to generate offer letters.
- Make sure `wkhtmltopdf` is installed and accessible.

## Deployment Notes
- For **Heroku**: Add `wkhtmltopdf` buildpack or install it in your build script.
- Set all environment variables in your platform's dashboard.
- Use a production database for scale (Postgres recommended).

## Extending the Project
- Add an admin dashboard to view/manage candidates.
- Integrate real code execution (e.g., Judge0 API) for coding tests.
- Add more robust grading or AI-based interview evaluation.
- Add more stages or custom questions.

## License
MIT 