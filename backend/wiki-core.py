"""
Wiki Module
==========

Implements wiki functionality including page creation, editing, and history.
Also handles wiki-specific content processing and permissions.

Features:
- Wiki page CRUD operations
- Revision history
- Content processing with wiki links
- User ban list checking
- Talk page integration
"""

import re
import sqlite3
import urllib.parse
from flask import (
    Blueprint, render_template, session, redirect, request,
    url_for, flash, abort, jsonify
)
from datetime import datetime
from backend.database import get_db
from backend.content import ContentProcessor
from backend.auth import rate_limit
from backend.config import Config

wiki_blueprint = Blueprint("wiki", __name__)

def check_edit_permission(page_id, user_id):
    """
    Check if user has permission to edit a wiki page.
    Returns (allowed, reason) tuple.
    """
    if not user_id:
        return False, "You must be logged in to edit pages"
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user is a moderator (moderators can edit any page)
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM moderators
                WHERE user_id = ?
            )
        """, (user_id,))
        is_moderator = bool(cursor.fetchone()[0])
        
        if is_moderator:
            return True, None
        
        # Get page creator
        cursor.execute("""
            SELECT created_by
            FROM wiki_pages
            WHERE id = ?
        """, (page_id,))
        page = cursor.fetchone()
        
        if not page:
            return False, "Page not found"
        
        # Check if user is banned by page creator
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM user_bans
                WHERE user_id = ? AND banned_user_id = ?
            )
        """, (page['created_by'], user_id))
        is_banned = bool(cursor.fetchone()[0])
        
        if is_banned:
            return False, "You have been banned from editing this user's pages"
        
        return True, None

def process_wiki_links(content):
    """
    Process [[Wiki Link]] style links in content.
    Converts them to proper Markdown links to the wiki page.
    """
    def replace_link(match):
        page_title = match.group(1).strip()
        escaped_title = urllib.parse.quote(page_title.replace(' ', '_'))
        return f'[{page_title}](/wiki/page/{escaped_title})'
    
    # Replace [[Page Title]] with [Page Title](/wiki/page/Page_Title)
    pattern = r'\[\[(.*?)\]\]'
    return re.sub(pattern, replace_link, content)

def get_talk_thread(page_id):
    """Get the associated talk thread for a wiki page."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id
            FROM threads
            WHERE wiki_page_id = ? AND is_wiki = 1
            LIMIT 1
        """, (page_id,))
        thread = cursor.fetchone()
        return thread['id'] if thread else None

def create_talk_thread(page_id, page_title, user_id):
    """Create a new talk thread for a wiki page."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get page info
        cursor.execute("""
            SELECT group_id, category_id
            FROM wiki_pages
            WHERE id = ?
        """, (page_id,))
        page = cursor.fetchone()
        
        if not page:
            return None
        
        # Create talk thread
        cursor.execute("""
            INSERT INTO threads (
                title, created_by, group_id, category_id, is_wiki, wiki_page_id
            ) VALUES (?, ?, ?, ?, 1, ?)
        """, (
            f"Talk: {page_title}", 
            user_id, 
            page['group_id'], 
            page['category_id'],
            page_id
        ))
        thread_id = cursor.lastrowid
        
        # Create initial post
        cursor.execute("""
            INSERT INTO posts (thread_id, created_by, content)
            VALUES (?, ?, ?)
        """, (
            thread_id, 
            user_id, 
            f"Discussion page for wiki article: [{page_title}](/wiki/page/{urllib.parse.quote(page_title.replace(' ', '_'))})\n\nPlease use this thread to discuss changes, suggestions, or questions about the article."
        ))
        
        return thread_id

@wiki_blueprint.route("/")
def wiki_home():
    """Show wiki homepage with filtered list of pages."""
    # Redirect to the forum view with is_wiki=1
    return redirect(url_for('forum.view_threads', is_wiki=1))

@wiki_blueprint.route("/page/<path:title>")
def view_page(title):
    """View a wiki page."""
    # Decode URL-encoded title
    decoded_title = urllib.parse.unquote(title.replace('_', ' '))
    
    with get_db() as conn:
        cursor = conn.cursor()
        processor = ContentProcessor(conn)
        
        # Get page with group and category info
        cursor.execute("""
            SELECT p.*, 
                   u.username,
                   g.grouptext as group_name,
                   gc.category as category_name
            FROM wiki_pages p
            JOIN users u ON p.created_by = u.id
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN group_categories gc ON p.category_id = gc.id
            WHERE p.title = ?
        """, (decoded_title,))
        page = cursor.fetchone()
        
        # Check if page exists
        if not page:
            # Page not found, show creation page
            return render_template(
                'wiki/not_found.html', 
                title=decoded_title
            )
        
        # Process wiki links in content
        content_with_links = process_wiki_links(page['content'])
        
        # Render the content as HTML
        rendered_content = processor.render_markdown(content_with_links)
        
        # Get talk thread ID if it exists
        talk_thread_id = get_talk_thread(page['id'])
        
        # Check if current user can edit
        user_id = session.get('user_id')
        can_edit, edit_reason = check_edit_permission(page['id'], user_id)
        
        # Get revision count
        cursor.execute("""
            SELECT COUNT(*) as revision_count
            FROM wiki_revisions
            WHERE wiki_page_id = ?
        """, (page['id'],))
        revision_info = cursor.fetchone()
        revision_count = revision_info['revision_count'] if revision_info else 0
        
    return render_template(
        'wiki/page.html',
        page=page,
        rendered_content=rendered_content,
        talk_thread_id=talk_thread_id,
        can_edit=can_edit,
        edit_reason=edit_reason,
        revision_count=revision_count
    )

@wiki_blueprint.route("/page/<path:title>/edit", methods=["GET", "POST"])
@rate_limit()
def edit_page(title):
    """Edit a wiki page."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    # Decode URL-encoded title
    decoded_title = urllib.parse.unquote(title.replace('_', ' '))
    user_id = session.get('user_id')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get page
        cursor.execute("""
            SELECT *
            FROM wiki_pages
            WHERE title = ?
        """, (decoded_title,))
        page = cursor.fetchone()
        
        # Check if page exists
        if not page:
            abort(404)
        
        # Check edit permission
        can_edit, reason = check_edit_permission(page['id'], user_id)
        if not can_edit:
            flash(reason)
            return redirect(url_for('wiki.view_page', title=title))
        
        if request.method == "POST":
            # Get form data
            new_content = request.form.get('content', '').strip()
            edit_comment = request.form.get('edit_comment', '').strip()
            
            # Validate content
            if not new_content:
                flash("Content cannot be empty")
                return render_template(
                    'wiki/edit.html',
                    page=page,
                    edit_comment=edit_comment
                )
            
            # Check for conflicting edits
            cursor.execute("""
                SELECT updated_at
                FROM wiki_pages
                WHERE id = ? AND updated_at > ?
            """, (page['id'], request.form.get('last_updated')))
            conflict = cursor.fetchone()
            
            if conflict:
                flash("Warning: This page was modified while you were editing. Your changes have been saved, but you may want to review the page history.")
            
            # Add revision
            cursor.execute("""
                INSERT INTO wiki_revisions (
                    wiki_page_id, content, edited_by, edit_comment
                ) VALUES (?, ?, ?, ?)
            """, (page['id'], page['content'], user_id, edit_comment))
            
            # Update page content
            processor = ContentProcessor(conn)
            cursor.execute("""
                UPDATE wiki_pages
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_content, page['id']))
            
            # Create talk thread if it doesn't exist
            talk_thread_id = get_talk_thread(page['id'])
            if not talk_thread_id:
                create_talk_thread(page['id'], decoded_title, user_id)
            
            flash("Page updated successfully")
            return redirect(url_for('wiki.view_page', title=title))
        
        # GET request - show edit form
        return render_template(
            'wiki/edit.html',
            page=page,
            edit_comment=''
        )

@wiki_blueprint.route("/page/<path:title>/history")
def page_history(title):
    """Show revision history of a wiki page."""
    # Decode URL-encoded title
    decoded_title = urllib.parse.unquote(title.replace('_', ' '))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get page
        cursor.execute("""
            SELECT *
            FROM wiki_pages
            WHERE title = ?
        """, (decoded_title,))
        page = cursor.fetchone()
        
        # Check if page exists
        if not page:
            abort(404)
        
        # Get revisions with editor usernames
        cursor.execute("""
            SELECT r.*, u.username
            FROM wiki_revisions r
            JOIN users u ON r.edited_by = u.id
            WHERE r.wiki_page_id = ?
            ORDER BY r.created_at DESC
        """, (page['id'],))
        revisions = cursor.fetchall()
        
        # Add current version at the top
        cursor.execute("""
            SELECT u.username
            FROM users u
            JOIN wiki_pages p ON u.id = p.created_by
            WHERE p.id = ?
        """, (page['id'],))
        current_editor = cursor.fetchone()
        
        current_version = {
            'id': 'current',
            'content': page['content'],
            'edited_by': page['created_by'],
            'username': current_editor['username'] if current_editor else 'Unknown',
            'created_at': page['updated_at'],
            'edit_comment': 'Current version'
        }
        
    return render_template(
        'wiki/history.html',
        page=page,
        current_version=current_version,
        revisions=revisions
    )

@wiki_blueprint.route("/page/<path:title>/revision/<int:revision_id>")
def view_revision(title, revision_id):
    """View a specific revision of a wiki page."""
    # Decode URL-encoded title
    decoded_title = urllib.parse.unquote(title.replace('_', ' '))
    
    with get_db() as conn:
        cursor = conn.cursor()
        processor = ContentProcessor(conn)
        
        # Get page
        cursor.execute("""
            SELECT *
            FROM wiki_pages
            WHERE title = ?
        """, (decoded_title,))
        page = cursor.fetchone()
        
        # Check if page exists
        if not page:
            abort(404)
        
        # Get revision
        cursor.execute("""
            SELECT r.*, u.username
            FROM wiki_revisions r
            JOIN users u ON r.edited_by = u.id
            WHERE r.id = ? AND r.wiki_page_id = ?
        """, (revision_id, page['id']))
        revision = cursor.fetchone()
        
        if not revision:
            abort(404)
        
        # Process wiki links in revision content
        content_with_links = process_wiki_links(revision['content'])
        
        # Render the content as HTML
        rendered_content = processor.render_markdown(content_with_links)
        
    return render_template(
        'wiki/revision.html',
        page=page,
        revision=revision,
        rendered_content=rendered_content
    )

@wiki_blueprint.route("/page/<path:title>/compare", methods=["GET"])
def compare_revisions(title):
    """Compare two revisions of a wiki page."""
    # Decode URL-encoded title
    decoded_title = urllib.parse.unquote(title.replace('_', ' '))
    
    # Get revision IDs to compare
    from_id = request.args.get('from', type=int)
    to_id = request.args.get('to', type=int)
    
    if not from_id or not to_id:
        flash("Please select two revisions to compare")
        return redirect(url_for('wiki.page_history', title=title))
    
    with get_db() as conn:
        cursor = conn.cursor()
        processor = ContentProcessor(conn)
        
        # Get page
        cursor.execute("""
            SELECT *
            FROM wiki_pages
            WHERE title = ?
        """, (decoded_title,))
        page = cursor.fetchone()
        
        # Check if page exists
        if not page:
            abort(404)
        
        # Get "from" revision
        if from_id == 0:  # Current version
            from_revision = {
                'id': 0,
                'content': page['content'],
                'edited_by': page['created_by'],
                'created_at': page['updated_at'],
                'edit_comment': 'Current version'
            }
            
            cursor.execute("""
                SELECT username FROM users WHERE id = ?
            """, (page['created_by'],))
            user = cursor.fetchone()
            from_revision['username'] = user['username'] if user else 'Unknown'
        else:
            cursor.execute("""
                SELECT r.*, u.username
                FROM wiki_revisions r
                JOIN users u ON r.edited_by = u.id
                WHERE r.id = ? AND r.wiki_page_id = ?
            """, (from_id, page['id']))
            from_revision = cursor.fetchone()
        
        # Get "to" revision
        if to_id == 0:  # Current version
            to_revision = {
                'id': 0,
                'content': page['content'],
                'edited_by': page['created_by'],
                'created_at': page['updated_at'],
                'edit_comment': 'Current version'
            }
            
            cursor.execute("""
                SELECT username FROM users WHERE id = ?
            """, (page['created_by'],))
            user = cursor.fetchone()
            to_revision['username'] = user['username'] if user else 'Unknown'
        else:
            cursor.execute("""
                SELECT r.*, u.username
                FROM wiki_revisions r
                JOIN users u ON r.edited_by = u.id
                WHERE r.id = ? AND r.wiki_page_id = ?
            """, (to_id, page['id']))
            to_revision = cursor.fetchone()
        
        if not from_revision or not to_revision:
            flash("One or both revisions were not found")
            return redirect(url_for('wiki.page_history', title=title))
        
        # Process wiki links in both contents
        from_content = process_wiki_links(from_revision['content'])
        to_content = process_wiki_links(to_revision['content'])
        
        # Render both contents as HTML
        from_html = processor.render_markdown(from_content)
        to_html = processor.render_markdown(to_content)
        
    return render_template(
        'wiki/compare.html',
        page=page,
        from_revision=from_revision,
        to_revision=to_revision,
        from_html=from_html,
        to_html=to_html
    )

@wiki_blueprint.route("/page/<path:title>/talk")
def view_talk(title):
    """View or create talk page for a wiki page."""
    # Decode URL-encoded title
    decoded_title = urllib.parse.unquote(title.replace('_', ' '))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get page
        cursor.execute("""
            SELECT *
            FROM wiki_pages
            WHERE title = ?
        """, (decoded_title,))
        page = cursor.fetchone()
        
        # Check if page exists
        if not page:
            abort(404)
        
        # Get talk thread ID
        talk_thread_id = get_talk_thread(page['id'])
        
        # Create talk thread if it doesn't exist and user is logged in
        if not talk_thread_id and session.get('user_id'):
            talk_thread_id = create_talk_thread(
                page['id'], 
                decoded_title, 
                session['user_id']
            )
        
        if talk_thread_id:
            # Redirect to thread view
            return redirect(url_for('forum.view_thread', thread_id=talk_thread_id))
        else:
            # No talk page and user not logged in
            flash("Please log in to create a discussion page")
            return redirect(url_for('wiki.view_page', title=title))

@wiki_blueprint.route("/user/ban/<int:user_id>", methods=["POST"])
def ban_user(user_id):
    """Ban a user from editing pages created by the current user."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    current_user_id = session['user_id']
    
    # Don't allow banning yourself
    if user_id == current_user_id:
        flash("You cannot ban yourself")
        return redirect(url_for('forum.view_threads', is_wiki=1))
    
    # Don't allow banning moderators
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM moderators
                WHERE user_id = ?
            )
        """, (user_id,))
        is_moderator = bool(cursor.fetchone()[0])
        
        if is_moderator:
            flash("You cannot ban moderators")
            return redirect(url_for('forum.view_threads', is_wiki=1))
        
        # Ban the user
        try:
            cursor.execute("""
                INSERT INTO user_bans (user_id, banned_user_id)
                VALUES (?, ?)
            """, (current_user_id, user_id))
            
            # Get username for the flash message
            cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            flash(f"User {user['username'] if user else user_id} has been banned from editing your pages")
        except sqlite3.IntegrityError:
            flash("This user is already banned")
    
    return redirect(url_for('forum.view_threads', is_wiki=1))

@wiki_blueprint.route("/user/unban/<int:user_id>", methods=["POST"])
def unban_user(user_id):
    """Unban a user from editing pages created by the current user."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    current_user_id = session['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get username for the flash message
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        # Remove the ban
        cursor.execute("""
            DELETE FROM user_bans
            WHERE user_id = ? AND banned_user_id = ?
        """, (current_user_id, user_id))
        
        if cursor.rowcount > 0:
            flash(f"User {user['username'] if user else user_id} has been unbanned")
        else:
            flash("This user was not banned")
    
    return redirect(url_for('forum.view_threads', is_wiki=1))

@wiki_blueprint.route("/banned_users")
def banned_users():
    """View and manage users banned by the current user."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get users banned by the current user
        cursor.execute("""
            SELECT u.id, u.username, b.created_at
            FROM user_bans b
            JOIN users u ON b.banned_user_id = u.id
            WHERE b.user_id = ?
            ORDER BY u.username
        """, (session['user_id'],))
        banned_users = cursor.fetchall()
    
    return render_template('wiki/banned_users.html', banned_users=banned_users)

@wiki_blueprint.route("/search", methods=["GET"])
def search():
    """Search wiki pages."""
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('wiki/search.html', query='', results=None)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Search in titles and content
        cursor.execute("""
            SELECT p.*, 
                   u.username,
                   g.grouptext as group_name,
                   gc.category as category_name
            FROM wiki_pages p
            JOIN users u ON p.created_by = u.id
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN group_categories gc ON p.category_id = gc.id
            WHERE p.title LIKE ? OR p.content LIKE ?
            ORDER BY 
                CASE WHEN p.title LIKE ? THEN 0 ELSE 1 END,
                p.updated_at DESC
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        results = cursor.fetchall()
    
    return render_template('wiki/search.html', query=query, results=results)
