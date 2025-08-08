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

## 🔧 **Recent Fixes and Improvements**

### **Fixed Issues:**
- ✅ **Link Usage Logic**: Fixed the issue where links were marked as used immediately upon access. Now links are only marked as completed after the test/interview is finished.
- ✅ **CrewAI Agent Integration**: Improved agent configuration and result parsing with proper error handling.
- ✅ **Fallback Mode**: Added comprehensive fallback functionality when CrewAI is not available.
- ✅ **Flow Continuity**: Ensured proper flow through all stages (coding test → technical interview → HR interview → offer letter).
- ✅ **Error Handling**: Enhanced error handling for all CrewAI operations with graceful fallbacks.

### **Key Improvements:**
- **Robust Agent System**: Each agent now has proper error handling and fallback mechanisms
- **Better Result Parsing**: Improved JSON parsing for CrewAI results with multiple fallback strategies
- **Enhanced User Experience**: Users can now retake tests if they fail, and completed tests show results
- **Comprehensive Logging**: Added detailed logging for debugging and monitoring
- **Email Integration**: Improved email sending with proper error handling

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

### 🔒 Improved Link Management
- Links are only marked as completed after test/interview submission
- Users can retake tests if they fail
- Completed tests show results instead of error messages
- Automatic tracking of completion status with timestamps

## Process Flow

1. **Application Form** → CrewAI Resume Screening Agent
2. **Coding Test** → CrewAI Coding Assessment Agent (80% threshold)
3. **Technical Interview** → CrewAI Technical Interview Agent (80% threshold)
4. **HR Interview** → CrewAI HR Interview Agent (80% threshold)
5. **Offer Letter** → CrewAI Offer Letter Agent (automatic generation)

### **Stage Progression:**
- Each stage requires 80% or higher to proceed to the next
- Failed candidates receive detailed feedback
- Successful candidates automatically receive the next stage link
- All results are stored and can be viewed later

## CrewAI Agent Details

**Resume Screening Agent:**
- Analyzes candidate resumes and skills
- Determines initial fit for the position
- Provides screening recommendations

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
- **Robust Error Handling**: Comprehensive fallback mechanisms for reliability
- **Improved User Experience**: Better flow and feedback throughout the process

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
│   ├── hr_result.html
│   └── error.html
├── static/               # Static files
│   ├── css/
│   ├── js/
│   └── uploads/
└── utils/               # Utility modules
    ├── resume_parser.py
    ├── email_utils.py
    └── judge0_utils.py
```

## Troubleshooting

### Common Issues:

1. **CrewAI Import Errors**: The system includes fallback mechanisms when CrewAI is not available
2. **Email Sending Issues**: Check your email credentials and SMTP settings
3. **OpenAI API Errors**: Ensure your API key is valid and has sufficient credits
4. **Link Access Issues**: Links are now properly managed and only marked as completed after submission

### Debug Mode:

Access `/debug/states` to view current candidate states and debug information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 