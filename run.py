# run.py - Cross-platform development server
import os
import sys

def run():
    # Load env vars
    from dotenv import load_dotenv
    load_dotenv()
    
    # Import app after env loaded
    from app import app
    
    # Production: use gunicorn (Linux)
    if sys.platform != "win32" and os.environ.get("FLASK_ENV") == "production":
        print("🚀 Starting with Gunicorn (production)")
        from gunicorn.app.wsgiapp import run as gunicorn_run
        sys.argv = ["gunicorn", "wsgi:app", "--bind", f"0.0.0.0:{os.environ.get('PORT', 5000)}", "--workers", "2"]
        gunicorn_run()
    else:
        # Local: use waitress (Windows-compatible)
        print("🔧 Starting with Waitress (local development)")
        from waitress import serve
        port = int(os.environ.get("PORT", "5000"))
        serve(app, host="127.0.0.1", port=port)

if __name__ == "__main__":
    run()