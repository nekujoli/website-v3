from flask import Blueprint, render_template

wiki_blueprint = Blueprint("wiki", __name__)

@wiki_blueprint.route("/")
def wiki_home():
    return render_template("wiki.html")
