import os
import sys

# Ensure backend package and current directory are on sys.path
cwd = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(cwd, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if cwd not in sys.path:
    sys.path.insert(0, cwd)

from app.main import create_app

# Phusion Passenger ASGI/WSGI entry point
application = create_app()
