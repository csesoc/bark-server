"""
Runs the Flask Development Service
"""

from app import app

if __name__ == '__main__':
    app.run(port=7000, debug=True)
