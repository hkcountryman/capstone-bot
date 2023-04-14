"""Imports app to run as a WSGI server with Gunicorn.

See README.md for more information. Gunicorn could be started by referring to
this module, e.g., with `gunicorn -b 0.0.0.0:8080 'wsgi:app'`.
"""

from app import app

if __name__ == "__main__":
    app.run()
