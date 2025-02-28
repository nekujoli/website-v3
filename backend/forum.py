"""
Forum Module
===========

Implements forum functionality including threads, posts, and user interactions.
Handles thread permissions, post editing, and content management.

Features:
- Thread management (public/private)
- Post creation and editing
- Edit history tracking
- Image handling
- User permissions
"""

import sqlite3
from flask import (
    Blueprint, render_template, session, redirect, request,
    url_for, flash, jsonify, make_response, abort
)
from database import get_db
from content import ContentProcessor
from auth import rate_limit
from config import Config
from typing import List, Optional

forum_blueprint = Blueprint("forum", __name__)

def check_thread_access(thread_id: int, user_id: Optional[int]) -> bool:
    """Check if user has access to thread."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user is a moderator
        if user_id:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM moderators
                    WHERE user_id = ?
                )
            """, (user_id,))
            is_moderator = bool(cursor.fetchone()[0])
            
            if is_moderator:
                return True
        
        # Check if thread exists and is public or user has access
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM threads t
                LEFT JOIN thread_users tu ON t.id = tu.thread_id
                WHERE t.id = ? AND (
                    tu.thread_id IS NULL
                    OR tu.user_id = ?
                    OR t.created_by = ?
                )
            )
        """, (thread_id, user_id, user_id))
        
        return bool(cursor.fetchone()[0])

def check_post_access(post_id: int, user_id: Optional[int]) -> bool:
    """Check if user has access to post."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user is a moderator
        if user_id:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM moderators
                    WHERE user_id = ?
                )
            """, (user_id,))
            is_moderator = bool(cursor.fetchone()[0])
            
            if is_moderator:
                return True
        
        # Check if post exists and either:
        # 1. Has no restrictions (post_users entries)
        # 2. User is in post_users
        # 3. User is the post creator
        cursor.execute("""
            SELECT p.thread_id, p.created_by,
                  (SELECT COUNT(*) FROM post_users WHERE post_id = ?) as has_restrictions
            FROM posts p
            WHERE p.id = ?
        """, (post_id, post_id))
        post = cursor.fetchone()
        
        if not post:
            return False
            
        # First check thread access
        if not check_thread_access(post['thread_id'], user_id):
            return False
            
        # If post has no restrictions or user is post creator, allow access
        if post['has_restrictions'] == 0 or post['created_by'] == user_id:
            return True
            
        # Check if user is in post_users
        if user_id:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM post_users
                    WHERE post_id = ? AND user_id = ?
                )
            """, (post_id, user_id))
            return bool(cursor.fetchone()[0])
            
        return False

@forum_blueprint.route("/thread/<int:thread_id>")
def view_thread(thread_id: int):
    """Show posts in a thread."""
    user_id = session.get('user_id')
    
    if not check_thread_access(thread_id, user_id):
        abort(403)
    
    with get_db() as conn:
        cursor = conn.cursor()
        processor = ContentProcessor(conn)
        
        # Check if user is a moderator
        is_moderator = False
        if user_id:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM moderators
                    WHERE user_id = ?
                )
            """, (user_id,))
            is_moderator = bool(cursor.fetchone()[0])
        
        # Get thread info with group and category
        cursor.execute("""
            SELECT t.*, u.username,
                   g.grouptext as group_name,
                   gc.category as category_name
            FROM threads t
            JOIN users u ON t.created_by = u.id
            LEFT JOIN groups g ON t.group_id = g.id
            LEFT JOIN group_categories gc ON t.category_id = gc.id
            WHERE t.id = ?
        """, (thread_id,))
        thread = cursor.fetchone()
        
        if not thread:
            abort(404)
        
        # Get permitted users for the thread
        cursor.execute("""
            SELECT u.id, u.username
            FROM thread_users tu
            JOIN users u ON tu.user_id = u.id
            WHERE tu.thread_id = ?
            ORDER BY u.username
        """, (thread_id,))
        thread_users = cursor.fetchall()
        
        # Get posts
        cursor.execute("""
            SELECT 
                p.*, u.username,
                (SELECT COUNT(*) FROM post_edits WHERE post_id = p.id) as edit_count
            FROM posts p
            JOIN users u ON p.created_by = u.id
            WHERE p.thread_id = ?
            ORDER BY p.created_at ASC
        """, (thread_id,))
        original_posts = cursor.fetchall()
        
        # Process post content (creating a new list since Row objects are immutable)
        processed_posts = []
        for post in original_posts:
            # Convert Row to dict so we can modify it
            post_dict = dict(post)
            
            # Check if post has restrictions
            cursor.execute("""
                SELECT COUNT(*) as is_restricted 
                FROM post_users 
                WHERE post_id = ?
            """, (post_dict['id'],))
            
            restriction_info = cursor.fetchone()
            post_dict['is_restricted'] = restriction_info['is_restricted'] if restriction_info else 0
            
            # Check post access
            has_access = True
            if post_dict['is_restricted'] > 0:
                has_access = check_post_access(post_dict['id'], user_id)
            
            if has_access:
                # Get post users if the post is restricted
                post_dict['restricted_users'] = []
                if post_dict['is_restricted'] > 0:
                    cursor.execute("""
                        SELECT u.id, u.username
                        FROM post_users pu
                        JOIN users u ON pu.user_id = u.id
                        WHERE pu.post_id = ?
                        ORDER BY u.username
                    """, (post_dict['id'],))
                    post_dict['restricted_users'] = cursor.fetchall()
                
                # Render markdown to HTML for display
                post_dict['rendered_content'] = processor.render_markdown(post_dict['content'])
                processed_posts.append(post_dict)
        
        # Check if this thread is a report thread (in Moderation group, Reported Post category)
        is_report_thread = False
        reported_post_id = None
        
        if thread['group_name'] == 'Moderation' and thread['category_name'] == 'Reported Post':
            is_report_thread = True
            
            # Try to extract post ID from the first post content if it exists
            if processed_posts and 'post-' in processed_posts[0]['content']:
                import re
                match = re.search(r'post-(\d+)', processed_posts[0]['content'])
                if match:
                    reported_post_id = int(match.group(1))
        
        # Update last seen if logged in
        if user_id:
            cursor.execute("""
                UPDATE threads 
                SET last_seen_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (thread_id,))
    
    return render_template(
        "forum/thread.html", 
        thread=thread, 
        posts=processed_posts, 
        Config=Config,
        thread_users=thread_users,
        is_moderator=is_moderator,
        is_report_thread=is_report_thread,
        reported_post_id=reported_post_id
    )

@forum_blueprint.route("/thread/<int:thread_id>/post", methods=["POST"])
@rate_limit()
def new_post(thread_id: int):
    """Create a new post in a thread."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
        
    # Check thread access
    if not check_thread_access(thread_id, session['user_id']):
        abort(403)
    
    content = request.form.get('content', '').strip()
    if not content:
        flash("Post content cannot be empty")
        return redirect(url_for('forum.view_thread', thread_id=thread_id))
    
    with get_db() as conn:
        cursor = conn.cursor()
        processor = ContentProcessor(conn)
        
        # Create post with empty content initially
        cursor.execute("""
            INSERT INTO posts (thread_id, created_by, content)
            VALUES (?, ?, '')
        """, (thread_id, session['user_id']))
        post_id = cursor.lastrowid
        
        # Process content (convert base64 images to URLs) but keep as markdown
        processed_content, _ = processor.process_new_post(content, post_id)
        
        # Update post with processed markdown (not HTML)
        cursor.execute("""
            UPDATE posts 
            SET content = ?
            WHERE id = ?
        """, (processed_content, post_id))
        
        # Update thread timestamp
        cursor.execute("""
            UPDATE threads 
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (thread_id,))
        
    return redirect(url_for('forum.view_thread', thread_id=thread_id))

@forum_blueprint.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@rate_limit()
def edit_post(post_id: int):
    """Edit post if user is creator."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get post and check permissions
        cursor.execute("""
            SELECT p.*, t.id as thread_id
            FROM posts p
            JOIN threads t ON p.thread_id = t.id
            WHERE p.id = ?
        """, (post_id,))
        post = cursor.fetchone()
        
        if not post or post['created_by'] != session['user_id']:
            abort(403)

        if request.method == "POST":
            new_content = request.form.get('content', '').strip()
            
            # Store edit history with original markdown
            cursor.execute("""
                INSERT INTO post_edits (
                    post_id, edited_by, old_content, new_content
                )
                VALUES (?, ?, ?, ?)
            """, (post_id, session['user_id'], post['content'], new_content))
            
            # Process content but keep as markdown
            processor = ContentProcessor(conn)
            processed_content, _ = processor.process_new_post(new_content, post_id)
            
            # Update post with processed markdown (not HTML)
            cursor.execute("""
                UPDATE posts 
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (processed_content, post_id))
            
            return redirect(url_for(
                'forum.view_thread',
                thread_id=post['thread_id']
            ))
            
        return render_template('forum/edit_post.html', post=post)

@forum_blueprint.route("/post/<int:post_id>/history")
def post_history(post_id: int):
    """View edit history of a post."""
    with get_db() as conn:
        cursor = conn.cursor()
        processor = ContentProcessor(conn)
        
        # Get post info
        cursor.execute("""
            SELECT p.*, t.id as thread_id
            FROM posts p
            JOIN threads t ON p.thread_id = t.id
            WHERE p.id = ?
        """, (post_id,))
        post = cursor.fetchone()
        
        if not post or not check_thread_access(
            post['thread_id'],
            session.get('user_id')
        ):
            abort(403)
        
        # Get edit history
        cursor.execute("""
            SELECT pe.*, u.username
            FROM post_edits pe
            JOIN users u ON pe.edited_by = u.id
            WHERE post_id = ?
            ORDER BY created_at DESC
        """, (post_id,))
        edits = cursor.fetchall()
        
        # Process edit history content for display
        processed_edits = []
        for edit in edits:
            edit_dict = dict(edit)
            # Render markdown to HTML for display
            edit_dict['rendered_old_content'] = processor.render_markdown(edit_dict['old_content'])
            edit_dict['rendered_new_content'] = processor.render_markdown(edit_dict['new_content'])
            processed_edits.append(edit_dict)
        
    return render_template('forum/post_history.html', post=post, edits=processed_edits, Config=Config)

@forum_blueprint.route("/api/image/<int:image_id>")
def get_image(image_id: int):
    """Serve an image from the database."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get image info
        cursor.execute("""
            SELECT i.*, p.thread_id
            FROM images i
            JOIN posts p ON i.post_id = p.id
            WHERE i.id = ?
        """, (image_id,))
        image = cursor.fetchone()
        
        if not image or not check_thread_access(
            image['thread_id'],
            session.get('user_id')
        ):
            abort(404)
        
        response = make_response(image['data'])
        response.headers.set('Content-Type', image['content_type'])
        response.headers.set(
            'Content-Disposition',
            f'inline; filename="{image["filename"]}"'
        )
        return response

@forum_blueprint.route("/api/search_users")
def search_users():
    """Search users by username."""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username 
            FROM users 
            WHERE username LIKE ? 
            LIMIT 10
        """, (f'%{query}%',))
        users = cursor.fetchall()
        
    return jsonify([{
        'id': user['id'],
        'username': user['username']
    } for user in users])

@forum_blueprint.route("/post/<int:post_id>/report", methods=["POST"])
@rate_limit()
def report_post(post_id: int):
    """Report a post to moderators."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    # Get the reason provided by the user
    reason = request.form.get('reason', '').strip()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get post and thread info
        cursor.execute("""
            SELECT p.*, t.title as thread_title, t.id as thread_id, 
                   u.username as post_author, ru.username as reporting_user
            FROM posts p
            JOIN threads t ON p.thread_id = t.id
            JOIN users u ON p.created_by = u.id
            JOIN users ru ON ru.id = ?
            WHERE p.id = ?
        """, (session['user_id'], post_id))
        post_info = cursor.fetchone()
        
        if not post_info:
            flash("Post not found")
            return redirect(url_for('forum.view_threads'))
        
        # Get all moderators
        cursor.execute("""
            SELECT u.id 
            FROM users u
            JOIN moderators m ON u.id = m.user_id
        """)
        moderators = [row['id'] for row in cursor.fetchall()]
        
        # Find or create "Moderation" group
        cursor.execute("SELECT id FROM groups WHERE grouptext = 'Moderation'")
        group = cursor.fetchone()
        
        if not group:
            cursor.execute("INSERT INTO groups (grouptext) VALUES ('Moderation')")
            group_id = cursor.lastrowid
        else:
            group_id = group['id']
        
        # Find or create "Reported Post" category under "Moderation" group
        cursor.execute("""
            SELECT id FROM group_categories 
            WHERE group_id = ? AND category = 'Reported Post'
        """, (group_id,))
        category = cursor.fetchone()
        
        if not category:
            cursor.execute("""
                INSERT INTO group_categories (group_id, category) 
                VALUES (?, 'Reported Post')
            """, (group_id,))
            category_id = cursor.lastrowid
        else:
            category_id = category['id']
        
        # Create report thread
        post_url = f"{request.host_url}forum/thread/{post_info['thread_id']}#post-{post_id}"
        report_title = f"Report: '{post_info['thread_title']}'"
        
        cursor.execute("""
            INSERT INTO threads (title, created_by, group_id, category_id)
            VALUES (?, ?, ?, ?)
        """, (report_title, session['user_id'], group_id, category_id))
        report_thread_id = cursor.lastrowid
        
        # Add moderators to thread_users
        for mod_id in moderators:
            cursor.execute("""
                INSERT INTO thread_users (thread_id, user_id)
                VALUES (?, ?)
            """, (report_thread_id, mod_id))
        
        # Create first post with report info
        report_content = f"""
User **{post_info['reporting_user']}** reported a post for your attention:

**Thread:** {post_info['thread_title']}  
**Author:** {post_info['post_author']}  
**Post Link:** [View Reported Post]({post_url})

"""
        
        if reason:
            report_content += f"""
**Reason for reporting:**  
{reason}
"""
        
        cursor.execute("""
            INSERT INTO posts (thread_id, created_by, content)
            VALUES (?, ?, ?)
        """, (report_thread_id, session['user_id'], report_content))
        
        flash("Post reported to moderators")
        
    return redirect(url_for('forum.view_thread', thread_id=post_info['thread_id']))

@forum_blueprint.route("/post/<int:post_id>/restrict", methods=["POST"])
def restrict_post(post_id: int):
    """Restrict a post to specific users (typically moderators)."""
    user_id = session.get('user_id')
    
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
    
    if not user_id or not is_moderator:
        abort(403)
    
    # Get the report thread ID from the form
    report_thread_id = request.form.get('report_thread_id', type=int)
    if not report_thread_id:
        flash("Missing report thread ID")
        return redirect(url_for('forum.view_threads'))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get post info
        cursor.execute("SELECT thread_id FROM posts WHERE id = ?", (post_id,))
        post = cursor.fetchone()
        
        if not post:
            flash("Post not found")
            return redirect(url_for('forum.view_threads'))
        
        # Get users who can see the report thread
        cursor.execute("""
            SELECT user_id 
            FROM thread_users 
            WHERE thread_id = ?
        """, (report_thread_id,))
        thread_users = [row['user_id'] for row in cursor.fetchall()]
        
        # Get all moderators
        cursor.execute("SELECT user_id FROM moderators")
        moderators = [row['user_id'] for row in cursor.fetchall()]
        
        # Combine users from both sources
        allowed_users = set(thread_users + moderators)
        
        # Clear any existing restrictions
        cursor.execute("DELETE FROM post_users WHERE post_id = ?", (post_id,))
        
        # Add restrictions for each user
        for user_id in allowed_users:
            cursor.execute("""
                INSERT INTO post_users (post_id, user_id)
                VALUES (?, ?)
            """, (post_id, user_id))
        
        flash("Post visibility restricted to moderators and report participants")
    
    # Redirect back to the report thread
    return redirect(url_for('forum.view_thread', thread_id=report_thread_id))

@forum_blueprint.route("/post/<int:post_id>/unrestrict", methods=["POST"])
def unrestrict_post(post_id: int):
    """Remove post restrictions, making it visible to anyone with thread access."""
    user_id = session.get('user_id')
    
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
    
    if not user_id or not is_moderator:
        abort(403)
    
    # Get the report thread ID from the form
    report_thread_id = request.form.get('report_thread_id', type=int)
    if not report_thread_id:
        flash("Missing report thread ID")
        return redirect(url_for('forum.view_threads'))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get post info
        cursor.execute("SELECT thread_id FROM posts WHERE id = ?", (post_id,))
        post = cursor.fetchone()
        
        if not post:
            flash("Post not found")
            return redirect(url_for('forum.view_threads'))
        
        # Remove all restrictions
        cursor.execute("DELETE FROM post_users WHERE post_id = ?", (post_id,))
        
        flash("Post visibility restored to normal")
    
    # Redirect back to the report thread
    return redirect(url_for('forum.view_thread', thread_id=report_thread_id))

@forum_blueprint.route("/thread/<int:thread_id>/add_user", methods=["POST"])
def add_thread_user(thread_id: int):
    """Add a user to a thread's allowed users list."""
    user_id = session.get('user_id')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if thread exists and user has appropriate permissions
        cursor.execute("""
            SELECT created_by FROM threads WHERE id = ?
        """, (thread_id,))
        thread = cursor.fetchone()
        
        if not thread:
            flash("Thread not found")
            return redirect(url_for('forum.view_threads'))
        
        # Check if user is a moderator
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM moderators
                WHERE user_id = ?
            )
        """, (user_id,))
        is_moderator = bool(cursor.fetchone()[0])
        
        # Only thread creator or moderators can add users
        if user_id != thread['created_by'] and not is_moderator:
            abort(403)
        
        # Get the user to add
        add_user_id = request.form.get('user_id', type=int)
        if not add_user_id:
            flash("No user selected")
            return redirect(url_for('forum.view_thread', thread_id=thread_id))
        
        # Check if the user exists
        cursor.execute("SELECT username FROM users WHERE id = ?", (add_user_id,))
        add_user = cursor.fetchone()
        if not add_user:
            flash("User not found")
            return redirect(url_for('forum.view_thread', thread_id=thread_id))
        
        # Add user to thread_users if not already there
        try:
            cursor.execute("""
                INSERT INTO thread_users (thread_id, user_id)
                VALUES (?, ?)
            """, (thread_id, add_user_id))
            flash(f"Added {add_user['username']} to thread")
        except sqlite3.IntegrityError:
            flash(f"{add_user['username']} already has access to this thread")
    
    return redirect(url_for('forum.view_thread', thread_id=thread_id))

@forum_blueprint.route("/thread/<int:thread_id>/remove_user/<int:remove_user_id>", methods=["POST"])
def remove_thread_user(thread_id: int, remove_user_id: int):
    """Remove a user from a thread's allowed users list."""
    user_id = session.get('user_id')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if thread exists and user has appropriate permissions
        cursor.execute("""
            SELECT created_by FROM threads WHERE id = ?
        """, (thread_id,))
        thread = cursor.fetchone()
        
        if not thread:
            flash("Thread not found")
            return redirect(url_for('forum.view_threads'))
        
        # Check if user is a moderator
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM moderators
                WHERE user_id = ?
            )
        """, (user_id,))
        is_moderator = bool(cursor.fetchone()[0])
        
        # Only thread creator or moderators can remove users
        if user_id != thread['created_by'] and not is_moderator:
            abort(403)
        
        # Get the username for the flash message
        cursor.execute("SELECT username FROM users WHERE id = ?", (remove_user_id,))
        remove_user = cursor.fetchone()
        
        # Remove the user from thread_users
        cursor.execute("""
            DELETE FROM thread_users
            WHERE thread_id = ? AND user_id = ?
        """, (thread_id, remove_user_id))
        
        if remove_user:
            flash(f"Removed {remove_user['username']} from thread")
    
    return redirect(url_for('forum.view_thread', thread_id=thread_id))

@forum_blueprint.route("/thread/<int:thread_id>/add_reporter", methods=["POST"])
def add_reporter_to_thread(thread_id: int):
    """Add the original reporter to a report thread."""
    user_id = session.get('user_id')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user is a moderator or has access to the thread
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM moderators
                WHERE user_id = ?
            )
        """, (user_id,))
        is_moderator = bool(cursor.fetchone()[0])
        
        if not is_moderator and not check_thread_access(thread_id, user_id):
            abort(403)
        
        # Get the first post to find reporter info
        cursor.execute("""
            SELECT p.id, p.created_by, u.username
            FROM posts p
            JOIN users u ON p.created_by = u.id
            WHERE p.thread_id = ?
            ORDER BY p.created_at ASC
            LIMIT 1
        """, (thread_id,))
        first_post = cursor.fetchone()
        
        if not first_post:
            flash("Could not find the reporter")
            return redirect(url_for('forum.view_thread', thread_id=thread_id))
        
        # Add reporter to thread_users
        try:
            cursor.execute("""
                INSERT INTO thread_users (thread_id, user_id)
                VALUES (?, ?)
            """, (thread_id, first_post['created_by']))
            flash(f"Added reporter ({first_post['username']}) to the discussion")
        except sqlite3.IntegrityError:
            flash(f"Reporter already has access to this thread")
    
    return redirect(url_for('forum.view_thread', thread_id=thread_id))

@forum_blueprint.route("/thread/<int:thread_id>/add_author", methods=["POST"])
def add_author_to_thread(thread_id: int):
    """Add the author of the reported post to a report thread."""
    user_id = session.get('user_id')
    reported_post_id = request.form.get('reported_post_id', type=int)
    
    if not reported_post_id:
        flash("Could not determine the reported post")
        return redirect(url_for('forum.view_thread', thread_id=thread_id))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user is a moderator or has access to the thread
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM moderators
                WHERE user_id = ?
            )
        """, (user_id,))
        is_moderator = bool(cursor.fetchone()[0])
        
        if not is_moderator and not check_thread_access(thread_id, user_id):
            abort(403)
        
        # Get the reported post author
        cursor.execute("""
            SELECT p.created_by, u.username
            FROM posts p
            JOIN users u ON p.created_by = u.id
            WHERE p.id = ?
        """, (reported_post_id,))
        reported_post = cursor.fetchone()
        
        if not reported_post:
            flash("Could not find the reported post")
            return redirect(url_for('forum.view_thread', thread_id=thread_id))
        
        # Add post author to thread_users
        try:
            cursor.execute("""
                INSERT INTO thread_users (thread_id, user_id)
                VALUES (?, ?)
            """, (thread_id, reported_post['created_by']))
            flash(f"Added post author ({reported_post['username']}) to the discussion")
        except sqlite3.IntegrityError:
            flash(f"Post author already has access to this thread")
    
    return redirect(url_for('forum.view_thread', thread_id=thread_id))

# This file contains updates to the forum.py view_threads route for improved filtering

@forum_blueprint.route("/")
def view_threads():
    """Show threads accessible to current user with filtering."""
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * Config.THREADS_PER_PAGE
    
    # Get filter parameters
    filter_group = request.args.get('group_id', type=int)
    filter_category = request.args.get('category_id', type=int)
    is_wiki = request.args.get('is_wiki', '0') == '1'
    
    # Store filter preferences if provided
    if 'group_id' in request.args:
        if filter_group is not None:
            session['filter_group'] = filter_group
        else:
            # If explicitly set to empty (All Groups), remove from session
            if 'filter_group' in session:
                session.pop('filter_group')
    elif 'filter_group' in session:
        filter_group = session.get('filter_group')
        
    if 'category_id' in request.args:
        if filter_category is not None:
            session['filter_category'] = filter_category
        else:
            # If explicitly set to empty (All Categories), remove from session
            if 'filter_category' in session:
                session.pop('filter_category')
    elif 'filter_category' in session:
        filter_category = session.get('filter_category')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all available groups for filter dropdown
        cursor.execute("""
            SELECT id, grouptext FROM groups ORDER BY grouptext
        """)
        all_groups = cursor.fetchall()
        
        # Get categories for the selected group
        categories = []
        if filter_group:
            cursor.execute("""
                SELECT id, category 
                FROM group_categories 
                WHERE group_id = ?
                ORDER BY category
            """, (filter_group,))
            categories = cursor.fetchall()
        
        # Different queries for logged in vs anonymous users
        query_parts = []
        query_params = []
        
        # Base query
        base_query = """
            SELECT DISTINCT 
                t.*, u.username,
                g.grouptext as group_name,
                gc.category as category_name,
                COUNT(p.id) as post_count,
                MAX(p.created_at) as last_post_at
            FROM threads t
            JOIN users u ON t.created_by = u.id
            LEFT JOIN groups g ON t.group_id = g.id
            LEFT JOIN group_categories gc ON t.category_id = gc.id
            LEFT JOIN thread_users tu ON t.id = tu.thread_id
            LEFT JOIN posts p ON t.id = p.thread_id
            WHERE t.is_wiki = ?
        """
        query_params.append(1 if is_wiki else 0)
        
        # Add group filter if selected
        if filter_group:
            query_parts.append("t.group_id = ?")
            query_params.append(filter_group)
            
        # Add category filter if selected
        if filter_category:
            query_parts.append("t.category_id = ?")
            query_params.append(filter_category)
        
        # Add user access restrictions
        if user_id:
            # Get the filtered groups for the user
            cursor.execute("""
                SELECT group_id 
                FROM user_groups 
                WHERE user_id = ? AND filter_on = 1
            """, (user_id,))
            filtered_groups = [row['group_id'] for row in cursor.fetchall()]
            
            # If no groups are filtered, show threads from all groups
            if filtered_groups:
                filtered_groups_str = ','.join('?' for _ in filtered_groups)
                query_parts.append(f"(t.group_id IS NULL OR t.group_id IN ({filtered_groups_str}))")
                query_params.extend(filtered_groups)
            
            # Add thread access control
            query_parts.append("""(
                tu.thread_id IS NULL 
                OR tu.user_id = ?
                OR t.created_by = ?
            )""")
            query_params.extend([user_id, user_id])
        else:
            # Anonymous users see all public threads
            query_parts.append("tu.thread_id IS NULL")
        
        # Combine all query parts
        where_clause = " AND ".join(query_parts) if query_parts else ""
        if where_clause:
            base_query += " AND " + where_clause
            
        final_query = base_query + """
            GROUP BY t.id
            ORDER BY last_post_at DESC
            LIMIT ? OFFSET ?
        """
        query_params.extend([Config.THREADS_PER_PAGE, offset])
        
        cursor.execute(final_query, query_params)
        threads = cursor.fetchall()
        
    return render_template("forum/thread_list.html", 
                          threads=threads, 
                          page=page,
                          groups=all_groups,
                          categories=categories,
                          selected_group=filter_group,
                          selected_category=filter_category,
                          is_wiki=is_wiki,
                          Config=Config)

# --- Now add the API endpoint to get categories for AJAX ---

@forum_blueprint.route("/api/categories/<int:group_id>")
def get_categories(group_id: int):
    """API endpoint to get categories for a specific group."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, category 
            FROM group_categories 
            WHERE group_id = ?
            ORDER BY category
        """, (group_id,))
        categories = cursor.fetchall()
        
    return jsonify([{
        'id': category['id'],
        'category': category['category']
    } for category in categories])

@forum_blueprint.route("/new_thread", methods=["GET", "POST"])
@rate_limit()
def new_thread():
    """Create new thread or wiki page with initial content."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    # Check if this is a wiki page creation
    is_wiki = request.args.get('is_wiki', '0') == '1'

    if request.method == "POST":
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        users = request.form.get('users', '').strip().split(',')
        group_id = request.form.get('group_id')
        category_id = request.form.get('category_id')
        is_wiki = request.form.get('is_wiki', '0') == '1'
        
        # Validate title length
        if len(title) > Config.MAX_TITLE_LENGTH:
            flash(f"Title must be {Config.MAX_TITLE_LENGTH} characters or less")
            return redirect(url_for('forum.new_thread', is_wiki=1 if is_wiki else 0))
        
        # Validate group and category
        if not group_id or not category_id:
            flash("Please select both a group and category")
            return redirect(url_for('forum.new_thread', is_wiki=1 if is_wiki else 0))
        
        # Verify the user has access to this group
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT filter_on FROM user_groups 
                WHERE user_id = ? AND group_id = ?
            """, (session['user_id'], group_id))
            
            group_access = cursor.fetchone()
            if not group_access or not group_access['filter_on']:
                flash("You don't have access to post in this group")
                return redirect(url_for('forum.new_thread', is_wiki=1 if is_wiki else 0))
            
            processor = ContentProcessor(conn)
            
            # Create thread with group and category
            cursor.execute("""
                INSERT INTO threads (title, created_by, group_id, category_id, is_wiki)
                VALUES (?, ?, ?, ?, ?)
            """, (title, session['user_id'], group_id, category_id, 1 if is_wiki else 0))
            thread_id = cursor.lastrowid
            
            # Add permitted users (if not wiki page)
            if not is_wiki and users and users[0]:
                user_values = [
                    (thread_id, int(user_id)) 
                    for user_id in users 
                    if user_id and user_id != str(session['user_id'])
                ]
                cursor.executemany("""
                    INSERT INTO thread_users (thread_id, user_id)
                    VALUES (?, ?)
                """, user_values)
            
            # Create first post with empty content initially
            cursor.execute("""
                INSERT INTO posts (thread_id, created_by, content)
                VALUES (?, ?, '')
            """, (thread_id, session['user_id']))
            post_id = cursor.lastrowid
            
            # Process content (convert base64 images to URLs) but keep as markdown
            processed_content, _ = processor.process_new_post(content, post_id)
            
            # Update post with processed markdown (not HTML)
            cursor.execute("""
                UPDATE posts 
                SET content = ?
                WHERE id = ?
            """, (processed_content, post_id))
            
            # If this is a wiki page, also create an entry in wiki_revisions
            if is_wiki:
                # This would normally happen after wiki tables are created
                # This is a placeholder for future implementation
                pass
            
        return redirect(url_for('forum.view_thread', thread_id=thread_id))
    
    # GET request - Fetch filtered groups for the form
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.id, g.grouptext 
            FROM groups g
            JOIN user_groups ug ON g.id = ug.group_id
            WHERE ug.user_id = ? AND ug.filter_on = 1
            ORDER BY g.grouptext
        """, (session.get('user_id'),))
        groups = cursor.fetchall()
        
    return render_template('forum/new_thread.html', 
                          groups=groups, 
                          Config=Config, 
                          is_wiki=is_wiki)
