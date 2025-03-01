#!/usr/bin/env python3
import sys
import os

# Add application directory to path
sys.path.insert(0, '/var/www/newsapnow.org')

# Set environment variables if needed
os.environ['FLASK_ENV'] = 'production'

# Import the app
from backend.server import app as application
