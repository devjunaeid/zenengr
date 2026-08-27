import os
import sys

# Ensure backend package and current directory are on sys.path
cwd = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(cwd, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if cwd not in sys.path:
    sys.path.insert(0, cwd)

from a2wsgi import ASGIMiddleware
from app.main import create_app

# Convert FastAPI ASGI application to WSGI for cPanel Phusion Passenger
fastapi_app = create_app()
application = ASGIMiddleware(fastapi_app)
