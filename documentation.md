# Website V3 Documentation

## Implementation Status

The website currently has the following features implemented and tested:

| Feature | Status | Notes |
|---------|--------|-------|
| User Registration | ✅ Complete | Username generation, token-based auth |
| User Login | ✅ Complete | Supports both permanent and one-time tokens |
| Forum - Thread List | ✅ Complete | Displays public and permitted private threads |
| Forum - Thread Creation | ✅ Complete | With title, content, and access control |
| Forum - Post Creation | ✅ Complete | Markdown with image support |
| Basic Styling | ✅ Complete | Bootstrap-based styling |

Features that are partially implemented or untested:

| Feature | Status | Notes |
|---------|--------|-------|
| Forum - Post Editing | ⚠️ Partial | Route exists but may have bugs |
| Forum - Edit History | ⚠️ Partial | Template exists but untested |
| Image Handling | ⚠️ Partial | Code exists but untested |
| Wiki System | ❌ Planned | Only placeholder routes exist |
| Translation | ❌ Planned | Database schema exists but no implementation |

## Development Environment

### Requirements

- Python 3.11 or higher
- SQLite 3
- Virtual environment (recommended)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd website-v3
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```bash
   python backend/init_db.py
   ```

5. Run the development server:
   ```bash
   python backend/server.py
   ```

6. The server will be available at `http://127.0.0.1:8000`

### Directory Structure

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
# Admin Documentation - User Administration

The website uses a simple role-based access control system:

- User ID 1 is always the administrator and has access to all admin functions
- Moderators are regular users who have been granted additional permissions
- Regular users have standard access to forum and wiki features

Admin users have access to special functionality through the admin dropdown menu in the navigation bar.

## Moderator Management

Moderators have the following capabilities:
- Edit any post (not just their own)
- Lock threads
- Hide inappropriate content

Moderators are managed through the admin panel, accessible only to the administrator (User ID 1).



## Testing Procedures

### Manual Testing

Currently, the project relies on manual testing for feature validation. Key test paths include:

1. **Authentication Flow**:
   - Register a new account
   - Save tokens from registration page
   - Log out and log back in with a permanent token
   - Log out and log back in with a one-time token (verify it works once)

2. **Forum Flow**:
   - Create a new thread
   - View the thread
   - Add a reply to the thread
   - Edit one of your posts
   - View the edit history

3. **Private Thread Flow**:
   - Create a thread with specific allowed users
   - Verify visibility works as expected
   - Try accessing private threads with unauthorized accounts

### Future Test Plans

- Implement automated unit tests using pytest
- Create integration tests for key user flows
- Implement CI/CD pipeline for automated testing

## Customization Points

### Templates

All templates are located in `frontend/templates/` and use Jinja2 templating engine. The main customization points are:

1. **Base Layout**: Edit `base.html` to change the overall site structure
2. **Forum Templates**: 
   - Thread list: `forum/thread_list.html`
   - Thread view: `forum/thread.html`
   - New thread form: `forum/new_thread.html`
   - Post editing: `forum/edit_post.html`
   - Edit history: `forum/post_history.html`
3. **Authentication Templates**:
   - Login: `auth/login.html`
   - Registration: `auth/register.html`
   - Token confirmation: `auth/confirm_tokens.html`

### Styling

1. **Bootstrap**: The site uses a local copy of Bootstrap in `frontend/static/bootstrap/`
2. **Custom CSS**: Customize `frontend/static/styles.css` for site-specific styling
3. **CSS Variables**: Key design variables are defined in the `:root` section of styles.css

### Configuration

Edit `config.py` to customize various system settings:

- Database path
- Authentication settings (token counts, hash algorithm)
- Forum settings (limits on threads/posts per page)
- Rate limiting
- Language support

## Image Processing

### Supported Formats

The system supports all standard web image formats:
- JPEG/JPG
- PNG
- GIF
- WebP

### Size Limitations

- Maximum dimension: 1200px (configured in `Config.MAX_IMAGE_DIMENSION`)
- Images larger than the maximum dimension are automatically resized
- Aspect ratio is preserved during resizing

### Storage Approach

- Images are stored in the SQLite database in the `images` table
- Each image is associated with a specific post
- Metadata stored includes:
  - Filename
  - Content type
  - Post ID
  - Creation timestamp

### Image Handling Process

1. When a user pastes an image or includes a base64-encoded image, it's extracted
2. The image is validated to ensure it's a valid image type
3. Large images are resized while preserving aspect ratio
4. The image is stored in the database
5. In the post, a URL is inserted that points to the image endpoint

## Translation Features

### Current Implementation

The database schema includes support for translations, but the feature is not yet fully implemented. The planned approach is:

### Language Support

Current supported languages (in config.py):
- English (en)
- French (fr)
- Spanish (es)

Future versions will support more languages.

### Translation Process (Planned)

1. Users select their preferred language during registration
2. Content is stored in its original language
3. When a user views content in a different language:
   - Check if a translation exists in the database
   - If not, use browser-side translation API
   - Cache the translation in the database for future use

### Translation Database Schema

The `translations` table stores:
- Source type (post, thread, etc.)
- Source ID
- Target language
- Translated text
- Translator type (user or API)
- Translator ID (if applicable)

## API Documentation

The forum provides the following API endpoints:

### User Search API

**Endpoint**: `/forum/api/search_users`
**Method**: GET
**Parameters**:
- `q`: Search query (minimum 2 characters)
**Returns**: JSON array of users matching the query
**Example Response**:
```json
[
  {"id": 1, "username": "johndoe"},
  {"id": 2, "username": "janedoe"}
]
```

### Image API

**Endpoint**: `/forum/api/image/<image_id>`
**Method**: GET
**Parameters**:
- `image_id`: ID of the image to retrieve
**Returns**: The binary image data with appropriate content type
**Access Control**: Only users with access to the thread containing the post with the image can view it

## Deployment Process

### Production Setup

For production deployment, follow these steps:

1. **Set Environment Variables**:
   ```bash
   export SECRET_KEY="your-secure-secret-key"
   export DEBUG="False"
   export DB_PATH="/path/to/production/database.db"
   ```

2. **Use a Production WSGI Server**:
   
   Example with Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn --bind 0.0.0.0:8000 backend.server:app
   ```

   Example with uWSGI:
   ```bash
   pip install uwsgi
   uwsgi --http 0.0.0.0:8000 --module backend.server:app
   ```

3. **Set Up a Reverse Proxy**:
   
   Example Nginx configuration:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. **Database Considerations**:
   - For production, consider using a more robust database like PostgreSQL
   - Implement regular backups
   - Consider database migrations for updates

5. **Security Recommendations**:
   - Use HTTPS (Let's Encrypt provides free certificates)
   - Set secure cookie settings
   - Implement proper rate limiting
   - Consider adding CSRF protection
   - Enable Content Security Policy headers

### Scaling Considerations

For handling more traffic:
- Consider using multiple worker processes
- Implement a separate media server for image storage
- Add caching with Redis or Memcached
- Consider containerization with Docker for easier deployment

## Future Development

Planned features for upcoming versions:

1. **Wiki System**: Complete implementation of the wiki functionality
2. **Translation API Integration**: Fully implement the translation features
3. **User Profiles**: Add customizable user profiles
4. **Notifications**: Implement a notification system for thread updates
5. **Search Functionality**: Add full-text search for forum and wiki content
6. **API Expansion**: Provide a more comprehensive API for integration
7. **Mobile Optimization**: Further improve the mobile experience
