import os
import sys
import traceback

cwd = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(cwd, "backend")
venv_dir = "/home/enginee2/virtualenv/api-zenengr.synafeia.com/3.12"
site_packages_lib = os.path.join(venv_dir, "lib", "python3.12", "site-packages")
site_packages_lib64 = os.path.join(venv_dir, "lib64", "python3.12", "site-packages")

for path in [backend_dir, cwd, site_packages_lib, site_packages_lib64]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# Explicitly load production environment variables from .env
for env_file in [os.path.join(backend_dir, ".env"), os.path.join(cwd, ".env")]:
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k:
                            os.environ[k] = v
        except Exception:
            pass

try:
    from a2wsgi import ASGIMiddleware
    from app.main import create_app

    fastapi_app = create_app()
    application = ASGIMiddleware(fastapi_app)
except Exception:
    error_trace = traceback.format_exc()

    def application(environ, start_response):
        status = "500 Internal Server Error"
        response_headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "*"),
            ("Access-Control-Allow-Headers", "*"),
        ]
        start_response(status, response_headers)
        output = f"=== ZenEngr Backend Startup Error ===\n\n{error_trace}\n\nPython: {sys.version}\nSys Path: {sys.path}"
        return [output.encode("utf-8")]
