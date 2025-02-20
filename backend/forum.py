from flask import Blueprint, render_template

forum_blueprint = Blueprint("forum", __name__)

@forum_blueprint.route("/")
def forum_home():
    return render_template("forum.html")
