Authentication Module
===================

Handles user authentication using a token-based system.
Supports both permanent and one-time tokens.

Features:
- Random username generation
- Secure token generation
- Token validation
- Session management
- Rate limiting
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from typing import Tuple, List, Dict
import secrets
import hashlib
import time
from functools import wraps
from database import get_db
from config import Config

auth_blueprint = Blueprint("auth", __name__)

def generate_six_char_string() -> str:
    """Generate a random 6-character username or token using syllables."""
    consonants = "bfgkhlnrstvwy"
    vowels = "aeiou"
    syllables = [c + v for c in consonants for v in vowels]
    return "".join(secrets.choice(syllables) for _ in range(3))

def hash_value(value: str) -> str:
    """Hash a value using configured algorithm (SHA-512)."""
    return hashlib.new(Config.HASH_ALGORITHM, value.encode()).hexdigest()

def generate_tokens() -> Dict[str, List[Tuple[str, str]]]:
    """Generate permanent and one-time tokens with their hashes."""
    permanent = [(t := generate_six_char_string(), hash_value(t)) 
                for _ in range(Config.PERMANENT_TOKEN_COUNT)]
    one_time = [(t := generate_six_char_string(), hash_value(t)) 
                for _ in range(Config.ONE_TIME_TOKEN_COUNT)]
    return {"permanent": permanent, "one_time": one_time}

# Rate limiting implementation
_rate_limits = {}

def rate_limit(max_requests: int = Config.MAX_REQUESTS_PER_WINDOW, 
               window: int = Config.RATE_LIMIT_WINDOW):
    """Rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            now = time.time()
            ip = request.remote_addr
            
            # Initialize or clean old requests
            if ip not in _rate_limits:
                _rate_limits[ip] = []
            _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < window]
            
            # Check limit
            if len(_rate_limits[ip]) >= max_requests:
                return "Rate limit exceeded", 429
            
            _rate_limits[ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

@auth_blueprint.route("/register", methods=["GET", "POST"])
@rate_limit()
def register():
    """Register new user and generate their tokens."""
    if request.method == "POST":
        language = request.form.get("language", Config.DEFAULT_LANGUAGE)
        if language not in Config.SUPPORTED_LANGUAGES:
            flash("Unsupported language")
            return redirect(url_for("auth.register"))
            
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

        return render_template(
            "confirm_tokens.html",
            username=username,
            permanent=tokens["permanent"],
            one_time=tokens["one_time"]
        )

    return render_template("register.html")

@auth_blueprint.route("/login", methods=["GET", "POST"])
@rate_limit()
def login():
    """Authenticate user with token."""
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
            
            # Update user and token last_seen
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

            session["user_id"] = user_id
            session["user"] = username
            session["language"] = language
            
            return redirect(url_for("home"))

    return render_template("login.html")

@auth_blueprint.route("/logout")
def logout():
    """Clear user session."""
    session.clear()
    return redirect(url_for("home"))
