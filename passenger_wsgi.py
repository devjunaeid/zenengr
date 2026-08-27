import os
import sys

# 1. Point to cPanel Python 3.12 virtual environment interpreter & site-packages
VENV_PATH = "/home/enginee2/virtualenv/api-zenengr.synafeia.com/3.12"
INTERP = os.path.join(VENV_PATH, "bin", "python")
if sys.executable != INTERP and os.path.exists(INTERP):
    try:
        os.execl(INTERP, INTERP, *sys.argv)
    except Exception:
        pass

# 2. Ensure virtualenv site-packages, backend package, and current dir are in sys.path
cwd = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(cwd, "backend")
site_packages = os.path.join(VENV_PATH, "lib", "python3.12", "site-packages")

for path in [backend_dir, cwd, site_packages]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

from a2wsgi import ASGIMiddleware
from app.main import create_app

# 3. Convert FastAPI ASGI application to WSGI for cPanel Phusion Passenger
fastapi_app = create_app()
application = ASGIMiddleware(fastapi_app)
