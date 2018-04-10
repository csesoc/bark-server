"""
Runs the Flask Development Service
"""

from app import create_app
from config import Development

config = Development()
app = create_app(config)

if __name__ == '__main__':
    app.run(port=7000, debug=True)
