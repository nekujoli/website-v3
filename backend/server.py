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

Security Notes
-------------
- Uses session-based authentication
- CSRF protection via Flask-WTF
- Input sanitization in place
- Rate limiting on key endpoints
"""

from flask import Flask, render_template, session
from flask_wtf.csrf import CSRFProtect
from auth import auth_blueprint
from forum import forum_blueprint
from wiki import wiki_blueprint
from config import Config

app = Flask(__name__, 
    template_folder="../frontend/templates", 
    static_folder="../frontend/static"
)

# Configure app
app.config.from_object(Config)
app.config['SECRET_KEY'] = Config.SECRET_KEY
csrf = CSRFProtect(app)

# Register blueprints
app.register_blueprint(auth_blueprint, url_prefix="/auth")
app.register_blueprint(forum_blueprint, url_prefix="/forum")
app.register_blueprint(wiki_blueprint, url_prefix="/wiki")

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
