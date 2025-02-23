
A Flask-based forum and wiki system with authentication and translation support.

## Core Features
- Token-based authentication
- Forum with public/private threads
- Image support in posts with automatic resizing
- Edit history tracking
- Markdown content processing
- Multi-language support with browser-side translation

## Technical Stack
- Flask web framework
- SQLite database
- Bootstrap UI framework
- Browser Translation API
- Markdown processing with image support

## Directory Structure
```
website-v3/
├── backend/
│   ├── auth.py         # Authentication system
│   ├── content.py      # Content processing
│   ├── database.py     # Database management
│   ├── forum.py        # Forum functionality
│   ├── init_db.py      # Database initialization
│   ├── models.py       # Data models
│   ├── server.py       # Main application
│   └── wiki.py         # Wiki system (placeholder)
├── frontend/
│   ├── static/
│   │   ├── bootstrap/  # Local Bootstrap files
│   │   └── styles.css  # Custom styling
│   └── templates/      # Jinja2 templates
└── config.py           # Configuration
```

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Initialize database: `python backend/init_db.py`
3. Run server: `python backend/server.py`

## Development Notes
- All styling in styles.css, using Bootstrap where possible
- Forum posts use Markdown with image support
- Images auto-resize to max 1200px dimension
- Title length limited to 132 chars

## Security Features
- Token-based auth with one-time options
- Content sanitization
- Image validation
- Rate limiting
- SQL injection protection
