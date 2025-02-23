class Config:
    SECRET_KEY = 'replace_with_secure_key'  # Should be environment variable
    SQLITE_DB_PATH = 'database.db'
    TOKEN_LENGTH = 6
    HASH_ALGORITHM = 'sha512'
    PERMANENT_TOKEN_COUNT = 3
    ONE_TIME_TOKEN_COUNT = 50
    
    # Forum settings
    THREADS_PER_PAGE = 20
    POSTS_PER_PAGE = 50
    
    # Language settings
    SUPPORTED_LANGUAGES = ['en', 'fr', 'es']
    DEFAULT_LANGUAGE = 'en'
