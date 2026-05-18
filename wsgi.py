from app import app  # Import the Flask app instance

# Gunicorn looks for 'application' by default, but we can expose 'app' too
application = app

if __name__ == "__main__":
    app.run()