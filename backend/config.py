"""
Configuration Module
===================

Central configuration for the Website V3 application.
All configuration variables should be defined here.

Usage:
    from config import Config
    app.config.from_object(Config)
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Core settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_change_in_production')
    SQLITE_DB_PATH = os.getenv('DB_PATH', 'database.db')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Authentication
    TOKEN_LENGTH = 6
    HASH_ALGORITHM = 'sha512'
    PERMANENT_TOKEN_COUNT = 3
    ONE_TIME_TOKEN_COUNT = 50
    
    # Forum settings
    THREADS_PER_PAGE = 20
    POSTS_PER_PAGE = 50
    MAX_TITLE_LENGTH = 132
    MAX_IMAGE_DIMENSION = 1200
    
    # Rate limiting
    MAX_REQUESTS_PER_WINDOW = 100  # Maximum requests per window
    RATE_LIMIT_WINDOW = 3600       # Window size in seconds (1 hour)
    
    # Other existing settings...
    # Language settings
    SUPPORTED_LANGUAGES = [
        'en', 'fr', 'de', 'he', 'hi', 'it', 'ja', 'pl', 'ru', 'es', 
        'zh-CN', 'zh-TW', 'af', 'ar', 'hy', 'be', 'bg', 'ca', 'iw'
        'hr', 'cs', 'da', 'nl', 'eo', 'et', 'tl', 'fi', 'el', 
        'hu', 'is', 'id', 'ko', 'lv', 'lt', 'no', 'fa', 'pt', 
        'ro', 'sr', 'sk', 'sl', 'sw', 'sv', 'th', 'tr', 'uk', 'vi'
    ]
    DEFAULT_LANGUAGE = 'en'
    
    # Rate limiting
    RATE_LIMIT_WINDOW = 3600  # 1 hour
    MAX_REQUESTS_PER_WINDOW = 100

    # Color scheme
    COLORS = {
        'MASTER': '#1e1636',  # Master color (not directly used in UI)
        
        # Background progression from darkest to lighter
        'PAGE_BACKGROUND': '#06040b',      # Outermost (darkest)
        'CARD_BACKGROUND': '#161028',      # Card/container background
        'ELEMENT_BACKGROUND': '#261c44',   # UI element background
        'HIGHLIGHT_BACKGROUND': '#362861', # Highlighted/active elements
        
        # Foreground progression from subtle to prominent
        'SUBTLE_TEXT': '#86848a',          # Muted/secondary text
        'STANDARD_TEXT': '#9690a8',        # Regular text
        'PROMINENT_TEXT': '#a69cc3',       # Important text, headings
        'HIGHLIGHT_TEXT': '#b6a8e0'        # Highlighted text, links
    }
