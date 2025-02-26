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
        
        # Check if thread exists and is public
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

@forum_blueprint.route("/")
def view_threads():
    """Show threads accessible to current user."""
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * Config.THREADS_PER_PAGE
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Different queries for logged in vs anonymous users
        if user_id:
            cursor.execute("""
                SELECT DISTINCT 
                    t.*, u.username,
                    COUNT(p.id) as post_count,
                    MAX(p.created_at) as last_post_at
                FROM threads t
                JOIN users u ON t.created_by = u.id
                LEFT JOIN thread_users tu ON t.id = tu.thread_id
                LEFT JOIN posts p ON t.id = p.thread_id
                WHERE 
                    tu.thread_id IS NULL 
                    OR tu.user_id = ?
                    OR t.created_by = ?
                GROUP BY t.id
                ORDER BY last_post_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, user_id, Config.THREADS_PER_PAGE, offset))
        else:
            cursor.execute("""
                SELECT DISTINCT 
                    t.*, u.username,
                    COUNT(p.id) as post_count,
                    MAX(p.created_at) as last_post_at
                FROM threads t
                JOIN users u ON t.created_by = u.id
                LEFT JOIN thread_users tu ON t.id = tu.thread_id
                LEFT JOIN posts p ON t.id = p.thread_id
                WHERE tu.thread_id IS NULL
                GROUP BY t.id
                ORDER BY last_post_at DESC
                LIMIT ? OFFSET ?
            """, (Config.THREADS_PER_PAGE, offset))
        
        threads = cursor.fetchall()
        
    return render_template("forum/thread_list.html", 
                               threads=threads, 
                               page=page,
                               Config=Config)

@forum_blueprint.route("/thread/<int:thread_id>")
def view_thread(thread_id: int):
    """Show posts in a thread."""
    user_id = session.get('user_id')
    
    if not check_thread_access(thread_id, user_id):
        abort(403)
    
    with get_db() as conn:
        cursor = conn.cursor()
        processor = ContentProcessor(conn)
        
        # Get thread info
        cursor.execute("""
            SELECT t.*, u.username
            FROM threads t
            JOIN users u ON t.created_by = u.id
            WHERE t.id = ?
        """, (thread_id,))
        thread = cursor.fetchone()
        
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
            # Render markdown to HTML for display
            post_dict['rendered_content'] = processor.render_markdown(post_dict['content'])
            processed_posts.append(post_dict)
        
        # Update last seen if logged in
        if user_id:
            cursor.execute("""
                UPDATE threads 
                SET last_seen_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (thread_id,))
    
    return render_template("forum/thread.html", thread=thread, posts=processed_posts, Config=Config)

@forum_blueprint.route("/new_thread", methods=["GET", "POST"])
@rate_limit()
def new_thread():
    """Create new thread with initial post."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    if request.method == "POST":
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        users = request.form.get('users', '').strip().split(',')
        group_id = request.form.get('group_id')
        category_id = request.form.get('category_id')
        
        # Validate title length
        if len(title) > Config.MAX_TITLE_LENGTH:
            flash(f"Title must be {Config.MAX_TITLE_LENGTH} characters or less")
            return redirect(url_for('forum.new_thread'))
        
        # Validate group and category
        if not group_id or not category_id:
            flash("Please select both a group and category")
            return redirect(url_for('forum.new_thread'))
        
        with get_db() as conn:
            cursor = conn.cursor()
            processor = ContentProcessor(conn)
            
            # Create thread with group and category
            cursor.execute("""
                INSERT INTO threads (title, created_by, group_id, category_id)
                VALUES (?, ?, ?, ?)
            """, (title, session['user_id'], group_id, category_id))
            thread_id = cursor.lastrowid
            
            # Add permitted users
            if users and users[0]:
                user_values = [
                    (thread_id, int(user_id)) 
                    for user_id in users 
                    if user_id != session['user_id']
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
            
        return redirect(url_for('forum.view_thread', thread_id=thread_id))
    
    # GET request - Fetch groups for the form
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, grouptext FROM groups ORDER BY grouptext")
        groups = cursor.fetchall()
        
    return render_template('forum/new_thread.html', groups=groups, Config=Config)

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
        'id': cat['id'],
        'category': cat['category']
    } for cat in categories])

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
