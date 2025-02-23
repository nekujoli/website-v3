Wiki Module
==========

Placeholder for future wiki functionality.
Currently only provides basic routing.

TODO:
- Add page creation/editing
- Add revision history
- Add search functionality
- Add categories/tags
"""

from flask import Blueprint, render_template, session
from database import get_db
from auth import rate_limit

wiki_blueprint = Blueprint("wiki", __name__)

@wiki_blueprint.route("/")
def wiki_home():
    """Show wiki homepage."""
    return render_template("wiki.html")

@wiki_blueprint.route("/page/<path:page_path>")
def view_page(page_path):
    """View wiki page. Currently a placeholder."""
    return render_template("wiki_page.html", path=page_path)
