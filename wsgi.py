"""
Expose the flask app for serving by a WSGI Server
"""

from app import create_app
from config import Production

config = Production()
app = create_app(config)

