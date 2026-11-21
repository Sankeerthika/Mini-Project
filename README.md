# AI Meeting Intelligence & Commitment Tracking Platform

A full-stack web application that helps organizations manage meetings using AI. The platform uses Whisper for speech-to-text transcription and Google Gemini for meeting analysis, action item extraction, and task management.

## Features

- User authentication & authorization (Admin, Manager, Employee roles)
- Meeting audio/video upload and transcription using Whisper
- AI-powered meeting analysis using Google Gemini (summary, decisions, action items)
- Task management with assignments, deadlines, and status tracking
- Email notifications for assigned tasks
- Team progress monitoring with dashboards

## Tech Stack

### Frontend
- React.js 18
- Vite
- Tailwind CSS
- Axios (HTTP client)
- React Router (navigation)
- Recharts (data visualization)

### Backend
- Python 3.10+
- FastAPI
- SQLAlchemy 2.0 (ORM)
- PostgreSQL (database)
- JWT Authentication
- bcrypt (password hashing)
- SMTP (email)

### AI Services
- OpenAI Whisper (speech-to-text)
- Google Gemini API (meeting analysis)

## Project Structure

```
AI-Meeting-Intelligence/
│
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Page-level components
│   │   ├── layouts/           # Layout components (sidebar, navbar, etc.)
│   │   ├── services/          # API service calls (Axios)
│   │   ├── context/           # React context providers (auth, etc.)
│   │   ├── App.jsx            # Main app component with routing
│   │   ├── main.jsx           # React entry point
│   │   └── index.css          # Global styles with Tailwind
│   ├── .env                   # Frontend environment variables
│   ├── index.html
│   ├── vite.config.js         # Vite configuration
│   ├── tailwind.config.js     # Tailwind CSS config
│   ├── postcss.config.js      # PostCSS config
│   └── package.json           # NPM dependencies
│
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── database.py        # Database connection setup
│   │   ├── dependencies.py    # Shared dependencies (auth, etc.)
│   │   ├── models/            # SQLAlchemy models
│   │   │   └── models.py
│   │   ├── schemas/           # Pydantic schemas (request/response)
│   │   │   └── schemas.py
│   │   ├── routers/           # API route handlers
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── meetings.py
│   │   │   └── tasks.py
│   │   ├── services/          # Business logic services
│   │   │   ├── email_service.py
│   │   │   ├── transcription_service.py
│   │   │   └── meeting_analysis_service.py
│   │   └── utils/             # Helper utilities
│   │       └── security.py    # JWT and password utilities
│   ├── uploads/               # Stored meeting recordings
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Backend environment variables
│
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Google Gemini API key
- (Optional) FFmpeg for audio processing (required by Whisper)

---

## Setup Instructions

### 1. Set Up the Backend

#### a. Create a virtual environment and install dependencies:
```bash
cd backend
python -m venv venv

# On Windows (PowerShell):
venv\Scripts\Activate.ps1

# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

#### b. Install AI dependencies (optional for now, required later):
```bash
# Whisper (speech-to-text)
pip install openai-whisper

# Google Gemini client
pip install google-generativeai

# FFmpeg (required by Whisper for audio processing)
# On Windows: Download from https://ffmpeg.org/download.html
# On macOS: brew install ffmpeg
# On Linux: sudo apt-get install ffmpeg
```

#### c. Configure environment variables:
Open `backend/.env` and update the following:
```
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_PASSWORD=your_postgres_password
DATABASE_NAME=ai_meeting_db
DATABASE_USERNAME=postgres

SECRET_KEY=generate_a_long_random_string_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password
EMAIL_FROM=your_email@gmail.com
```

#### d. Create PostgreSQL database:
```sql
CREATE DATABASE ai_meeting_db;
```

#### e. Start the backend server:
```bash
uvicorn app.main:app --reload
```
The backend will run at http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Alternative Docs (ReDoc): http://localhost:8000/redoc

---

### 2. Set Up the Frontend

#### a. Install dependencies:
```bash
cd frontend
npm install
```

#### b. Configure environment variables:
The file `frontend/.env` already has:
```
VITE_API_URL=http://localhost:8000/api
```

#### c. Start the development server:
```bash
npm run dev
```
The frontend will run at http://localhost:3000

---

## Current Status

This project currently has **only the basic structure and configuration** set up. No functional features are implemented yet. The next modules to implement are:

1. **Authentication Module** - User registration, login, JWT token handling
2. **User Management** - User CRUD operations, role management
3. **Meeting Module** - Upload recordings, transcription, AI analysis
4. **Task Management** - Create, assign, and track tasks
5. **Dashboard & Reports** - Team progress, statistics, charts
6. **Email Notifications** - Task assignment notifications

### Next Steps

To continue development, confirm that the project structure and basic configuration look good, and I will implement the Authentication module next.
