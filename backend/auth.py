from flask import Blueprint, render_template, request, redirect, url_for, session

auth_blueprint = Blueprint("auth", __name__)

# Dummy users for now
users = {"admin": "password123"}

@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username] == password:
            session["user"] = username
            return redirect(url_for("home"))
        return "Invalid login"

    return render_template("login.html")

@auth_blueprint.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users:
            return "Username already exists"
        users[username] = password
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth_blueprint.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))
