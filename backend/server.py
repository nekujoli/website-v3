"""
Website V3 Server
================

Main server application module that initializes Flask and registers blueprints.

Architecture
-----------
The application uses a modular blueprint structure:
- auth: User authentication and management
- forum: Discussion forum functionality
- wiki: Knowledge base system
- admin: Administrative functions (user ID 1 only)

Security Notes
-------------
- Uses session-based authentication
- CSRF protection via Flask-WTF
- Input sanitization in place
- Rate limiting on key endpoints
"""

from flask import Flask, render_template, session
from flask_wtf.csrf import CSRFProtect
from backend.auth import auth_blueprint
from backend.forum import forum_blueprint
from backend.wiki import wiki_blueprint
from backend.admin import admin_blueprint
from backend.config import Config
from datetime import datetime
from backend.database import get_db

app = Flask(__name__, 
    template_folder="../frontend/templates", 
    static_folder="../frontend/static"
)

# Configure app
app.config.from_object(Config)
app.config['SECRET_KEY'] = Config.SECRET_KEY
csrf = CSRFProtect(app)

# Add datetime filter
@app.template_filter('datetime')
def format_datetime(value):
    """Format a datetime object for display."""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    return value.strftime('%B %d, %Y at %I:%M %p')

# Register blueprints
app.register_blueprint(auth_blueprint, url_prefix="/auth")
app.register_blueprint(forum_blueprint, url_prefix="/forum")
app.register_blueprint(wiki_blueprint, url_prefix="/wiki")
app.register_blueprint(admin_blueprint, url_prefix="/admin")

# Get moderators for navbar
@app.context_processor
def inject_moderators():
    """Add moderators to template context for navbar."""
    moderators = []
    if session.get('user_id'):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM moderators")
            moderators = cursor.fetchall()
    return {'moderators': moderators}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(
        host="127.0.0.1", 
        port=8000, 
        debug=Config.DEBUG
    )
