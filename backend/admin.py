"""
Admin Module
===========

Handles administrative functions for the website.
Currently includes moderator management and user blocking/restoration.

Only accessible to User ID 1 (administrator) and moderators.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from backend.database import get_db
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

def moderator_required(f):
    """Decorator to restrict access to moderators and administrators."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login'))
            
        # Check if user is admin (ID 1)
        if user_id == 1:
            return f(*args, **kwargs)
            
        # Check if user is a moderator
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM moderators
                    WHERE user_id = ?
                )
            """, (user_id,))
            is_moderator = bool(cursor.fetchone()[0])
            
        if not is_moderator:
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

@admin_blueprint.route("/user_groups")
def user_groups():
    """Manage user's group filter settings."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get user's groups and filter settings
        cursor.execute("""
            SELECT g.id, g.grouptext, ug.filter_on
            FROM groups g
            LEFT JOIN user_groups ug ON g.id = ug.group_id AND ug.user_id = ?
            ORDER BY g.grouptext
        """, (user_id,))
        groups = cursor.fetchall()
        
    return render_template('admin/user_groups.html', groups=groups)

@admin_blueprint.route("/user_groups/update", methods=["POST"])
def update_user_groups():
    """Update user's group filter settings."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    # Get groups to filter on
    filtered_groups = request.form.getlist('group_id', type=int)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all groups
        cursor.execute("SELECT id FROM groups")
        all_groups = [row['id'] for row in cursor.fetchall()]
        
        # Update each group's filter status
        for group_id in all_groups:
            # Determine if this group should be filtered on
            filter_on = 1 if group_id in filtered_groups else 0
            
            # Update or insert the user_group record
            cursor.execute("""
                INSERT OR REPLACE INTO user_groups (user_id, group_id, filter_on, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, group_id, filter_on))
    
    flash("Group preferences updated successfully")
    return redirect(url_for('admin.user_groups'))

@admin_blueprint.route("/users/block")
@moderator_required
def block_users():
    """View and block/restore users."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all non-admin/non-moderator users
        cursor.execute("""
            SELECT u.id, u.username,
                   (SELECT COUNT(*) FROM user_groups 
                    WHERE user_id = u.id AND filter_on = 1) as active_groups,
                   (SELECT COUNT(*) FROM user_groups 
                    WHERE user_id = u.id) as total_groups
            FROM users u
            WHERE u.id != 1 
            AND u.id NOT IN (SELECT user_id FROM moderators)
            ORDER BY u.username
        """)
        users = cursor.fetchall()
        
        # Get moderators for display (to show they can't be blocked)
        cursor.execute("""
            SELECT u.id, u.username, 'Moderator' as role
            FROM users u
            JOIN moderators m ON u.id = m.user_id
            WHERE u.id != 1
            UNION
            SELECT 1, u.username, 'Administrator' as role
            FROM users u
            WHERE u.id = 1
            ORDER BY role, username
        """)
        protected_users = cursor.fetchall()
        
    return render_template(
        "admin/block_users.html", 
        users=users,
        protected_users=protected_users
    )

@admin_blueprint.route("/users/block/<int:user_id>", methods=["POST"])
@moderator_required
def block_user(user_id):
    """Block a user by restricting them to Moderation group only."""
    # Safety check - prevent blocking admin or moderators
    if user_id == 1:
        flash("Cannot block administrator")
        return redirect(url_for('admin.block_users'))
        
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user is a moderator
        cursor.execute("SELECT 1 FROM moderators WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            flash("Cannot block moderators")
            return redirect(url_for('admin.block_users'))
        
        # Get username for messages
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            flash("User not found")
            return redirect(url_for('admin.block_users'))
            
        # Find Moderation group ID
        cursor.execute("SELECT id FROM groups WHERE grouptext = 'Moderation'")
        moderation_group = cursor.fetchone()
        if not moderation_group:
            flash("Moderation group not found")
            return redirect(url_for('admin.block_users'))
            
        # Remove all user_groups entries for this user
        cursor.execute("DELETE FROM user_groups WHERE user_id = ?", (user_id,))
        
        # Add only the Moderation group with filter_on = 1
        cursor.execute("""
            INSERT INTO user_groups (user_id, group_id, filter_on)
            VALUES (?, ?, 1)
        """, (user_id, moderation_group['id']))
        
        flash(f"User {user['username']} has been restricted to Moderation group only")
    
    return redirect(url_for('admin.block_users'))

@admin_blueprint.route("/users/restore/<int:user_id>", methods=["POST"])
@moderator_required
def restore_user(user_id):
    """Restore a user's access to all groups."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get username for messages
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            flash("User not found")
            return redirect(url_for('admin.block_users'))
            
        # Remove all user_groups entries for this user
        cursor.execute("DELETE FROM user_groups WHERE user_id = ?", (user_id,))
        
        # Add all groups with filter_on = 1
        cursor.execute("SELECT id FROM groups")
        groups = cursor.fetchall()
        
        for group in groups:
            cursor.execute("""
                INSERT INTO user_groups (user_id, group_id, filter_on)
                VALUES (?, ?, 1)
            """, (user_id, group['id']))
        
        flash(f"User {user['username']} has been restored access to all groups")
    
    return redirect(url_for('admin.block_users'))
