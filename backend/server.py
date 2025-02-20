from flask import Flask, render_template
from auth import auth_blueprint
from forum import forum_blueprint
from wiki import wiki_blueprint

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")
#app = Flask(__name__)
app.secret_key = "secret"

# Register blueprints (modular structure)
app.register_blueprint(auth_blueprint, url_prefix="/auth")
app.register_blueprint(forum_blueprint, url_prefix="/forum")
app.register_blueprint(wiki_blueprint, url_prefix="/wiki")

@app.route("/")
def home():
    """Render homepage."""
    return render_template("index.html")

@app.route("/about")
def about():
    """Render about page."""
    return render_template("about.html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
