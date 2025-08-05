# AI-Powered Hiring Pipeline (CrewAI Version)

An intelligent hiring system that uses **CrewAI agents** to evaluate candidates through multiple stages with comprehensive analysis and 80% threshold scoring.

## 🚀 **New: CrewAI Implementation**

This project now uses **CrewAI** - a powerful framework for orchestrating role-playing AI agents. The system maintains all existing functionalities while leveraging specialized AI agents for each stage of the hiring process.

### **CrewAI Agents:**

1. **Resume Screening Agent** - Evaluates candidate fit and initial screening
2. **Coding Assessment Agent** - Creates and evaluates coding tests
3. **Technical Interview Agent** - Conducts technical interviews
4. **HR Interview Agent** - Assesses cultural fit and professionalism
5. **Offer Letter Agent** - Generates professional offer letters

## Features

### 🤖 AI-Powered Evaluation (CrewAI Agents)
- **Resume Screening**: AI agent analyzes resumes and determines candidate fit
- **Coding Assessment**: AI agent creates questions and evaluates code quality
- **Technical Interview**: AI agent conducts technical interviews with depth analysis
- **HR Interview**: AI agent assesses cultural fit and communication skills
- **Offer Letter**: AI agent generates personalized offer letters

### 📊 80% Threshold System
- All stages require 80% or higher to pass
- Detailed scoring on multiple criteria
- Comprehensive feedback for improvement

### 📧 Automated Communication
- Email notifications at each stage
- Detailed feedback with scores
- HTML-based offer letter generation for successful candidates

### 🔒 Single-Use Test Links
- Each test link can only be accessed once
- Prevents multiple attempts and ensures test integrity
- Automatic tracking of link usage with timestamps
- Graceful error handling for expired or used links

## Process Flow

1. **Application Form** → CrewAI Resume Screening Agent
2. **Coding Test** → CrewAI Coding Assessment Agent
3. **Technical Interview** → CrewAI Technical Interview Agent
4. **HR Interview** → CrewAI HR Interview Agent
5. **Offer Letter** → CrewAI Offer Letter Agent

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

## Security Features

### Single-Use Link Implementation
The system implements a robust single-use link mechanism to ensure test integrity:

- **Usage Tracking**: Each candidate state includes boolean flags for each test type (`coding_test_used`, `tech_interview_used`, `hr_interview_used`)
- **Timestamp Recording**: When a link is first accessed, the system records the exact timestamp
- **Legacy Support**: Existing candidates without usage tracking are automatically upgraded
- **Error Handling**: Clear error messages for expired, invalid, or already-used links
- **Debug Endpoint**: `/debug/states` provides visibility into link usage status

**How it works:**
1. When a candidate accesses a test link, the system checks if it's been used before
2. If unused, the link is marked as used and the test proceeds
3. If already used, an error page is shown with appropriate messaging
4. All usage is persisted to the candidate states file for reliability

## CrewAI Architecture

### Agent Roles and Responsibilities:

**Resume Screening Agent:**
- Analyzes candidate resumes and skills
- Determines initial fit for the position
- Provides detailed reasoning for decisions

**Coding Assessment Agent:**
- Generates unique coding questions
- Evaluates code quality and correctness
- Provides comprehensive feedback

**Technical Interview Agent:**
- Creates personalized technical questions
- Evaluates technical depth and knowledge
- Assesses problem-solving abilities

**HR Interview Agent:**
- Generates HR interview questions
- Evaluates cultural fit and communication
- Assesses professionalism and soft skills

**Offer Letter Agent:**
- Creates personalized offer letters
- Ensures professional formatting
- Includes all necessary details

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

3. Run the CrewAI application:
```bash
python crewai_app.py
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
   - **Start Command**: `gunicorn crewai_app:app`
   - **Python Version**: 3.11.0

5. **Click Deploy** and wait for the build to complete

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

## Benefits of CrewAI Implementation

- **Specialized Agents**: Each stage has a dedicated AI agent with specific expertise
- **Better Context Understanding**: Agents maintain context across the hiring process
- **Improved Decision Making**: More sophisticated evaluation with agent collaboration
- **Scalable Architecture**: Easy to add new agents or modify existing ones
- **Enhanced Feedback**: More detailed and contextual feedback from specialized agents
- **Consistent Quality**: Standardized evaluation across all candidates

## Technology Stack

- **Backend**: Flask (Python)
- **AI Framework**: CrewAI + OpenAI GPT-4
- **Email**: Flask-Mail
- **Code Execution**: Judge0 API
- **UI**: Bootstrap 5
- **Offer Letters**: HTML-based (no external dependencies)
- **Production**: Gunicorn WSGI server

## File Structure

```
ai_hiring_pipeline/
├── crewai_app.py           # Main CrewAI Flask application
├── app.py                  # Original Flask application (legacy)
├── main.py                 # Original CrewAI CLI version
├── requirements.txt        # Python dependencies (updated for CrewAI)
├── gunicorn.conf.py       # Production server config
├── render.yaml            # Render deployment config
├── Procfile               # Heroku deployment config
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── templates/            # HTML templates
│   ├── form.html
│   ├── coding_test.html
│   ├── coding_result.html
│   ├── tech_interview.html
│   ├── tech_result.html
│   ├── hr_interview.html
│   └── hr_result.html
└── utils/                # Utility modules
    ├── resume_parser.py
    ├── email_utils.py
    └── judge0_utils.py
```

## Troubleshooting

### Common Issues

1. **CrewAI import errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`
2. **Email not sending**: Check your email credentials and enable "Less secure app access" or use app passwords
3. **OpenAI API errors**: Verify your API key and ensure you have sufficient credits
4. **Port issues**: The app automatically uses the PORT environment variable set by Render
5. **Build failures**: Ensure all dependencies are listed in requirements.txt
6. **Agent errors**: Check that your OpenAI API key has access to GPT-4 models

### Support

For deployment issues, check the platform-specific documentation:
- [Render Documentation](https://render.com/docs)
- [Heroku Documentation](https://devcenter.heroku.com/)
- [Railway Documentation](https://docs.railway.app/)
- [CrewAI Documentation](https://docs.crewai.com/)

## Migration from Original Version

If you're upgrading from the original Flask version:

1. **Install new dependencies**: `pip install -r requirements.txt`
2. **Update your deployment**: Change start command to `gunicorn crewai_app:app`
3. **Test the new implementation**: The CrewAI version maintains all existing functionality
4. **Monitor performance**: CrewAI agents may take slightly longer but provide better results

The CrewAI implementation maintains 100% compatibility with existing data and templates while providing enhanced AI capabilities through specialized agents. 