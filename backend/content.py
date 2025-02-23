Content Processing Module
========================

Handles content processing, storage, and retrieval for forum posts.
Includes image processing and markdown rendering.

Features:
- Markdown processing
- Image handling and resizing
- Content sanitization
- HTML cleaning
"""

import markdown
import bleach
import magic
import re
from flask import url_for
from typing import List, Tuple, Optional
import base64
from PIL import Image
from io import BytesIO
from config import Config

class ContentProcessor:
    def __init__(self, db_connection):
        """Initialize content processor with database connection."""
        self.conn = db_connection
        
        # Configure markdown
        self.md = markdown.Markdown(
            extensions=['extra', 'nl2br', 'fenced_code', 'tables']
        )
        
        # Configure HTML cleaning
        self.allowed_tags = bleach.ALLOWED_TAGS + [
            'img', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'hr', 'br', 'pre', 'code'
        ]
        self.allowed_attrs = {
            **bleach.ALLOWED_ATTRIBUTES,
            'img': ['src', 'alt', 'title'],
            'a': ['href', 'title'],
            'code': ['class']
        }

    def resize_image(self, image_data: bytes) -> bytes:
        """
        Resize image if it exceeds maximum dimensions.
        Maintains aspect ratio and optimizes file size.
        """
        img = Image.open(BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            bg = Image.new('RGB', img.size, 'WHITE')
            bg.paste(img, mask=img.split()[3])
            img = bg
        
        # Check if resize needed
        width, height = img.size
        if width > Config.MAX_IMAGE_DIMENSION or height > Config.MAX_IMAGE_DIMENSION:
            ratio = min(Config.MAX_IMAGE_DIMENSION / width, 
                       Config.MAX_IMAGE_DIMENSION / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save optimized
        output = BytesIO()
        format = img.format or 'JPEG'
        img.save(output, 
                 format=format,
                 quality=85, 
                 optimize=True)
        return output.getvalue()

    def store_image(self, post_id: int, img_data: bytes, 
                    mime_type: str, alt_text: str) -> int:
        """Store image in database and return its ID."""
        cursor = self.conn.cursor()
        
        # Generate filename
        cursor.execute(
            "SELECT COUNT(*) FROM images WHERE post_id = ?", 
            (post_id,)
        )
        img_count = cursor.fetchone()[0]
        filename = f'image_{post_id}_{img_count}.{mime_type.split("/")[1]}'
        
        # Store image
        cursor.execute("""
            INSERT INTO images (post_id, filename, content_type, data)
            VALUES (?, ?, ?, ?)
        """, (post_id, filename, mime_type, img_data))
        
        return cursor.lastrowid

    def process_new_post(self, content: str, post_id: int) -> Tuple[str, List[int]]:
        """
        Process new post content:
        - Extract and store images
        - Convert markdown to safe HTML
        Returns processed content and list of image IDs.
        """
        img_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^\)]+)\)'
        images = []
        
        def replace_image(match):
            alt_text, mime_subtype, b64_data = match.groups()
            
            try:
                # Decode and validate image
                img_data = base64.b64decode(b64_data)
                mime = magic.from_buffer(img_data, mime=True)
                
                if not mime.startswith('image/'):
                    return f'[Invalid image type: {mime}]'
                
                # Resize if needed
                img_data = self.resize_image(img_data)
                
                # Store and get ID
                image_id = self.store_image(
                    post_id, img_data, mime, alt_text
                )
                images.append(image_id)
                
                # Return markdown with URL
                return f'![{alt_text}]({url_for("forum.get_image", image_id=image_id)})'
                
            except Exception as e:
                return f'[Image processing error: {str(e)}]'
        
        # Replace base64 images with URLs
        content = re.sub(img_pattern, replace_image, content)
        
        # Convert markdown to safe HTML
        html = self.md.convert(content)
        safe_html = bleach.clean(
            html,
            tags=self.allowed_tags,
            attributes=self.allowed_attrs
        )
        
        return safe_html, images

    def process_existing_post(self, content: str) -> str:
        """
        Process existing post content for display.
        Converts markdown to safe HTML.
        """
        html = self.md.convert(content)
        return bleach.clean(
            html,
            tags=self.allowed_tags,
            attributes=self.allowed_attrs
        )
