# AI-Powered Hiring Pipeline

An intelligent hiring system that uses AI to evaluate candidates through multiple stages with comprehensive analysis and 80% threshold scoring.

## Features

### 🤖 AI-Powered Evaluation
- **Coding Assessment**: AI analyzes code for correctness, quality, efficiency, and best practices
- **Technical Interview**: AI evaluates technical knowledge, depth, and practical understanding
- **HR Interview**: AI assesses professionalism, cultural fit, and communication skills

### 📊 80% Threshold System
- All stages require 80% or higher to pass
- Detailed scoring on multiple criteria
- Comprehensive feedback for improvement

### 📧 Automated Communication
- Email notifications at each stage
- Detailed feedback with scores
- HTML-based offer letter generation for successful candidates

## Process Flow

1. **Application Form** → Resume parsing and initial screening
2. **Coding Test** → AI analysis of code quality and correctness
3. **Technical Interview** → AI evaluation of technical knowledge
4. **HR Interview** → AI assessment of cultural fit and professionalism
5. **Offer Letter** → Automated HTML offer generation for successful candidates

## Evaluation Criteria

### Coding Assessment (80% threshold)
- Correctness (problem solving)
- Code Quality (structure, readability)
- Efficiency (time/space complexity)
- Edge Case Handling
- Documentation

### Technical Interview (80% threshold)
- Accuracy of technical information
- Completeness of answers
- Depth of knowledge
- Clarity of explanation
- Practical application

### HR Interview (80% threshold)
- Relevance to question
- Professionalism
- Clarity of communication
- Honesty and authenticity
- Cultural fit

## Local Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables in `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_email_password
SECRET_KEY=your_secret_key
```

3. Run the application:
```bash
python app.py
```

## Deployment

### Render Deployment (Recommended)

1. **Fork/Clone** this repository to your GitHub account

2. **Connect to Render**:
   - Go to [render.com](https://render.com)
   - Sign up/Login with your GitHub account
   - Click "New +" → "Web Service"
   - Connect your repository

3. **Configure Environment Variables** in Render dashboard:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `MAIL_USERNAME`: Your email address
   - `MAIL_PASSWORD`: Your email password or app password
   - `SECRET_KEY`: A random secret key (Render can generate this)
   - `RAPIDAPI_KEY`: Your RapidAPI key for Judge0 (optional - system works without it)
   - `MAIL_SERVER`: `smtp.gmail.com`
   - `MAIL_PORT`: `587`
   - `MAIL_USE_TLS`: `true`

4. **Deploy Settings**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Python Version**: 3.11.0

5. **Click Deploy** and wait for the build to complete

### Alternative Deployment Options

#### Heroku
```bash
# Install Heroku CLI
heroku create your-app-name
git push heroku main
```

#### Railway
```bash
# Install Railway CLI
railway login
railway init
railway up
```

#### Vercel
```bash
# Install Vercel CLI
vercel login
vercel
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `MAIL_USERNAME` | Email for sending notifications | Yes |
| `MAIL_PASSWORD` | Email password or app password | Yes |
| `SECRET_KEY` | Flask secret key | Yes |
| `RAPIDAPI_KEY` | RapidAPI key for Judge0 code execution (optional) | No |
| `MAIL_SERVER` | SMTP server (default: smtp.gmail.com) | No |
| `MAIL_PORT` | SMTP port (default: 587) | No |
| `MAIL_USE_TLS` | Use TLS (default: true) | No |

**Note**: If `RAPIDAPI_KEY` is not provided, the system will use mock code execution for testing purposes.

## Templates

- `coding_result.html` - Displays coding test results with AI feedback
- `tech_result.html` - Shows technical interview results with analysis
- `hr_result.html` - Presents HR interview results with evaluation and offer letter link

## Benefits

- **Objective Evaluation**: AI provides consistent, unbiased assessment
- **Detailed Feedback**: Candidates receive comprehensive analysis
- **Quality Assurance**: 80% threshold ensures high standards
- **Automated Process**: Reduces manual review time
- **Scalable**: Handles multiple candidates efficiently
- **No External Dependencies**: HTML-based offer letters work without additional software
- **Easy Deployment**: Ready for Render, Heroku, Railway, and other platforms

## Technology Stack

- **Backend**: Flask (Python)
- **AI**: OpenAI GPT-4
- **Email**: Flask-Mail
- **Code Execution**: Judge0 API
- **UI**: Bootstrap 5
- **Offer Letters**: HTML-based (no external dependencies)
- **Production**: Gunicorn WSGI server

## File Structure

```
ai_hiring_pipeline/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── gunicorn.conf.py      # Production server config
├── render.yaml           # Render deployment config
├── Procfile              # Heroku deployment config
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── templates/           # HTML templates
│   ├── form.html
│   ├── coding_test.html
│   ├── coding_result.html
│   ├── tech_interview.html
│   ├── tech_result.html
│   ├── hr_interview.html
│   └── hr_result.html
└── utils/               # Utility modules
    ├── resume_parser.py
    ├── email_utils.py
    └── judge0_utils.py
```

## Troubleshooting

### Common Issues

1. **Email not sending**: Check your email credentials and enable "Less secure app access" or use app passwords
2. **OpenAI API errors**: Verify your API key and ensure you have sufficient credits
3. **Port issues**: The app automatically uses the PORT environment variable set by Render
4. **Build failures**: Ensure all dependencies are listed in requirements.txt
5. **Missing requests module**: The requirements.txt includes all necessary dependencies
6. **Judge0 API errors**: The system works without RapidAPI key (uses mock execution)
7. **Import errors**: Make sure all utils files are present in the utils/ directory

### Support

For deployment issues, check the platform-specific documentation:
- [Render Documentation](https://render.com/docs)
- [Heroku Documentation](https://devcenter.heroku.com/)
- [Railway Documentation](https://docs.railway.app/) 