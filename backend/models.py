Data Models
==========

Dataclass definitions for database entities.
These provide type hints and validation for database operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class User:
    id: int
    username: str
    language: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

@dataclass
class Token:
    id: int
    user_id: int
    token_hash: str
    one_time: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    updated_at: datetime

@dataclass
class Thread:
    id: int
    title: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    allowed_users: List[int] = None  # IDs from thread_users table

@dataclass
class Post:
    id: int
    thread_id: int
    created_by: int
    content: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

@dataclass
class PostEdit:
    id: int
    post_id: int
    edited_by: int
    old_content: str
    new_content: str
    created_at: datetime

@dataclass
class Image:
    id: int
    post_id: int
    filename: str
    content_type: str
    data: bytes
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

@dataclass
class Translation:
    id: int
    source_type: str
    source_id: int
    language: str
    translated_text: str
    translator_type: str
    translator_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
