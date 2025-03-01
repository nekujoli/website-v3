"""
Database Initialization
======================

Creates and resets database tables.
Run this script to initialize a fresh database or reset an existing one.

Usage:
    python init_db.py
"""

import sqlite3
from backend.config import Config

def reset_database():
    """Initialize fresh database, dropping existing tables."""
    conn = sqlite3.connect(Config.SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS user_bans;")
    cursor.execute("DROP TABLE IF EXISTS wiki_revisions;")
    cursor.execute("DROP TABLE IF EXISTS post_users;")
    cursor.execute("DROP TABLE IF EXISTS translations;")
    cursor.execute("DROP TABLE IF EXISTS images;")
    cursor.execute("DROP TABLE IF EXISTS post_edits;")
    cursor.execute("DROP TABLE IF EXISTS posts;")
    cursor.execute("DROP TABLE IF EXISTS thread_users;")
    cursor.execute("DROP TABLE IF EXISTS moderators;")
    cursor.execute("DROP TABLE IF EXISTS threads;")
    cursor.execute("DROP TABLE IF EXISTS wiki_pages;")
    cursor.execute("DROP TABLE IF EXISTS tokens;")
    cursor.execute("DROP TABLE IF EXISTS users;")

    # Create users table first (no dependencies)
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        language TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CHECK (language IN ('en', 'fr', 'es'))
    );
    """)

    # Create tokens table (depends on users)
    cursor.execute("""
    CREATE TABLE tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL,
        one_time BOOLEAN NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Add moderators table (depends on users)
    cursor.execute("""
    CREATE TABLE moderators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id)
    );
    """)

    # Create wiki_pages table (depends on users and groups/categories)
    cursor.execute("""
    CREATE TABLE wiki_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE NOT NULL,
        content TEXT NOT NULL,
        created_by INTEGER NOT NULL,
        group_id INTEGER,
        category_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id),
        FOREIGN KEY (group_id) REFERENCES groups(id),
        FOREIGN KEY (category_id) REFERENCES group_categories(id)
    );
    """)

    # Create threads table (depends on wiki_pages and users)
    cursor.execute("""
    CREATE TABLE threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL CHECK(length(title) <= 132),
        created_by INTEGER NOT NULL,
        group_id INTEGER,
        category_id INTEGER,
        is_wiki BOOLEAN DEFAULT 0,
        wiki_page_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id),
        FOREIGN KEY (group_id) REFERENCES groups(id),
        FOREIGN KEY (category_id) REFERENCES group_categories(id),
        FOREIGN KEY (wiki_page_id) REFERENCES wiki_pages(id)
    );
    """)

    # Thread users table (depends on threads and users)
    cursor.execute("""
    CREATE TABLE thread_users (
        thread_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (thread_id, user_id),
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Posts table (depends on threads and users)
    cursor.execute("""
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id INTEGER NOT NULL,
        created_by INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );
    """)

    # Post users table (depends on posts and users)
    cursor.execute("""
    CREATE TABLE post_users (
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (post_id, user_id),
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Post edits table (depends on posts and users)
    cursor.execute("""
    CREATE TABLE post_edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        edited_by INTEGER NOT NULL,
        old_content TEXT NOT NULL,
        new_content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (edited_by) REFERENCES users(id)
    );
    """)

    # Images table (depends on posts)
    cursor.execute("""
    CREATE TABLE images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        content_type TEXT NOT NULL,
        data BLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    );
    """)

    # Translations table (depends on users)
    cursor.execute("""
    CREATE TABLE translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,
        source_id INTEGER NOT NULL,
        language TEXT NOT NULL,
        translated_text TEXT NOT NULL,
        translator_type TEXT NOT NULL,
        translator_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source_type, source_id, language),
        CHECK (language IN ('en', 'fr', 'es')),
        FOREIGN KEY (translator_id) REFERENCES users(id)
    );
    """)

    # Wiki revisions table (depends on wiki_pages and users)
    cursor.execute("""
    CREATE TABLE wiki_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wiki_page_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        edited_by INTEGER NOT NULL,
        edit_comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (wiki_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
        FOREIGN KEY (edited_by) REFERENCES users(id)
    );
    """)

    # User bans table (depends on users)
    cursor.execute("""
    CREATE TABLE user_bans (
        user_id INTEGER NOT NULL,
        banned_user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, banned_user_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (banned_user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Create indexes for wiki tables
    cursor.execute("""
    CREATE INDEX idx_wiki_page_title ON wiki_pages(title);
    """)
    
    cursor.execute("""
    CREATE INDEX idx_wiki_revision_page ON wiki_revisions(wiki_page_id);
    """)

    conn.commit()
    conn.close()
    print("Database reset complete.")

if __name__ == "__main__":
    reset_database()
