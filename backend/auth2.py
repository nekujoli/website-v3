@auth_blueprint.route("/register", methods=["GET", "POST"])
def register():
    """Handle new user registration."""
    # Redirect if already logged in
    if session.get('user'):
        return redirect(url_for('home'))
        
    if request.method == "POST":
        language = request.form["language"]
        username = generate_six_char_string()
        tokens = generate_tokens()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, language) VALUES (?, ?)", 
                (username, language)
            )
            user_id = cursor.lastrowid

            # Store permanent tokens
            for token, hash in tokens["permanent"]:
                cursor.execute(
                    "INSERT INTO tokens (user_id, token_hash, one_time) VALUES (?, ?, ?)", 
                    (user_id, hash, False)
                )
            
            # Store one-time tokens
            for token, hash in tokens["one_time"]:
                cursor.execute(
                    "INSERT INTO tokens (user_id, token_hash, one_time) VALUES (?, ?, ?)", 
                    (user_id, hash, True)
                )

        # Show tokens to user
        return render_template(
            "auth/confirm_tokens.html", 
            username=username, 
            permanent=tokens["permanent"], 
            one_time=tokens["one_time"]
        )

    # Show registration form
    return render_template("auth/register.html")

@auth_blueprint.route("/confirm_registration", methods=["POST"])
def confirm_registration():
    """Handle confirmation after tokens are displayed."""
    return redirect(url_for('home'))

@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with token."""
    if request.method == "POST":
        token = request.form.get("token", "").strip()
        token_hash = hash_value(token)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT users.id, users.username, users.language,
                       tokens.id as token_id, tokens.one_time
                FROM users 
                JOIN tokens ON users.id = tokens.user_id 
                WHERE tokens.token_hash = ?
            """, (token_hash,))
            result = cursor.fetchone()

            if not result:
                flash("Invalid token")
                return redirect(url_for("auth.login"))

            user_id, username, language, token_id, one_time = result
            
            # Update last seen timestamps
            cursor.execute(
                "UPDATE users SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            cursor.execute(
                "UPDATE tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (token_id,)
            )
            
            # Delete one-time token if used
            if one_time:
                cursor.execute("DELETE FROM tokens WHERE id = ?", (token_id,))

            # Set up user session
            session["user_id"] = user_id
            session["user"] = username
            session["language"] = language
            
            return redirect(url_for("home"))

    return render_template("auth/login.html")
