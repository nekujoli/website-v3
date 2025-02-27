"""
Admin Module
===========

Handles administrative functions for the website.
Currently includes moderator management.

Only accessible to User ID 1 (administrator).
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from database import get_db
from functools import wraps

admin_blueprint = Blueprint("admin", __name__)

def admin_required(f):
    """Decorator to restrict access to administrator only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') == 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_blueprint.route("/moderators")
@admin_required
def manage_moderators():
    """View and manage forum moderators."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all moderators with their usernames
        cursor.execute("""
            SELECT m.id, m.user_id, u.username
            FROM moderators m
            JOIN users u ON m.user_id = u.id
            ORDER BY u.username
        """)
        moderators = cursor.fetchall()
        
        # Get other users (non-moderators)
        cursor.execute("""
            SELECT u.id, u.username
            FROM users u
            WHERE u.id NOT IN (
                SELECT user_id FROM moderators
            )
            ORDER BY u.username
        """)
        users = cursor.fetchall()
        
    return render_template(
        "admin/moderators.html", 
        moderators=moderators,
        users=users
    )

@admin_blueprint.route("/moderators/add", methods=["POST"])
@admin_required
def add_moderator():
    """Add a new moderator."""
    user_id = request.form.get('user_id', type=int)
    
    if not user_id:
        flash("No user selected")
        return redirect(url_for('admin.manage_moderators'))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found")
            return redirect(url_for('admin.manage_moderators'))
        
        # Add as moderator if not already
        try:
            cursor.execute(
                "INSERT INTO moderators (user_id) VALUES (?)",
                (user_id,)
            )
            flash(f"Added {user['username']} as moderator")
        except sqlite3.IntegrityError:
            flash(f"{user['username']} is already a moderator")
    
    return redirect(url_for('admin.manage_moderators'))

@admin_blueprint.route("/moderators/remove/<int:moderator_id>", methods=["POST"])
@admin_required
def remove_moderator(moderator_id):
    """Remove a moderator."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get moderator info before deleting
        cursor.execute("""
            SELECT u.username
            FROM moderators m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (moderator_id,))
        moderator = cursor.fetchone()
        
        if not moderator:
            flash("Moderator not found")
            return redirect(url_for('admin.manage_moderators'))
        
        # Remove moderator
        cursor.execute("DELETE FROM moderators WHERE id = ?", (moderator_id,))
        flash(f"Removed {moderator['username']} from moderators")
    
    return redirect(url_for('admin.manage_moderators'))
