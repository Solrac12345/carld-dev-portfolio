# Carlos David Tamayo Montañez — AI Developer Portfolio

[![Live Demo](https://img.shields.io/badge/Live-Render-blue?logo=render)](https://your-app.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-lightgrey?logo=flask)](https://flask.palletsprojects.com)

AI-powered portfolio featuring a RAG-based knowledge assistant, multilingual support (EN/FR/ES), and interactive project showcases. Built with engineering rigor and production-ready patterns.

## ✨ Features

- 🤖 **AI Knowledge Assistant**: Ask questions about my background, projects, or skills — powered by Groq + TF-IDF retrieval
- 🌍 **Multilingual UI**: Switch between English, French, and Spanish instantly
- 📄 **Smart Resume Download**: Language-aware PDF delivery (`/resume/en`, `/resume/fr`, `/resume/es`)
- 🔍 **RAG Pipeline**: Local PDF indexing, semantic search, and grounded LLM responses
- 🛡️ **Security-First**: API keys via environment variables only; fail-fast validation

## 🚀 Local Setup

```bash
# 1. Clone and enter project
git clone https://github.com/YOUR_USERNAME/portfolio.git
cd portfolio

# 2. Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows/Git Bash

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env  # Then add your GROQ_API_KEY

# 5. Run locally
python run.py

## 📁 Project Structure
portfolio/
├── app.py                 # Flask backend + RAG logic
├── run.py                 # Cross-platform dev server (waitress/gunicorn)
├── wsgi.py                # Production entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Template for environment variables
├── .gitignore             # Excludes secrets, venv, cache
├── templates/
│   └── portfolio.html     # Frontend (Tailwind CDN + vanilla JS)
├── static/
│   ├── images/            # Profile photos, previews
│   └── videos/            # Project demo videos
└── pdfs/
    ├── EN.pdf, FR.pdf, ES.pdf  # Multilingual resumes
    └── *.pdf              # Knowledge base documents for RAG

🤝 Contributing
This is a personal portfolio. For security reasons, please do not submit PRs. Feel free to fork for learning purposes.

📄 License
MIT — See LICENSE file for details.

## 🔧 Also Create `.env.example` (Safe to Commit)

Create a file named `.env.example` with this content:

```env
# Copy to .env and add your real values
# NEVER commit .env to version control

GROQ_API_KEY=gsk_your_key_here
FLASK_ENV=development
PORT=5000