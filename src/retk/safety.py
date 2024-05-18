import os

from starlette.middleware.base import BaseHTTPMiddleware

vue_app_mode = os.getenv("VUE_APP_MODE", "local")

if vue_app_mode not in ["dev", "local"]:
    allow_origins = [
        "https://rethink.run",
        "https://www.rethink.run",
    ]
    csp_local = ""
    cookie_domain = "rethink.run"
    cookie_secure = True
else:
    allow_origins = [
        "*",
    ]
    csp_local = " http://localhost:* http://127.0.0.1:* https://cdn.jsdelivr.net "
    cookie_domain = None
    cookie_secure = False

cookie_samesite = "strict"


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        csp_header = "default-src 'self'; " \
                     f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {csp_local} https://www.googletagmanager.com; " \
                     f"style-src 'self' 'unsafe-inline' 'report-sample' {csp_local}; " \
                     "img-src * data: blob:; " \
                     f"connect-src 'self' {csp_local} https://www.google-analytics.com;"
        response.headers["Content-Security-Policy"] = csp_header
        return response


class FrameOptionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response
