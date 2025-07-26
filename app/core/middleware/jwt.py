from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from starlette.responses import JSONResponse
from jose import jwt, JWTError
from app.helpers.response import custom_json_response
from app.services.auth_service import AuthService
from app.helpers.log import logger


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.auth_service = AuthService()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.exclude_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return custom_json_response(success=False, code=401, error="Missing or invalid Authorization header")

        token = auth_header.split(" ")[1]
        
        try:
            payload = self.auth_service.decode_token(token)
            request.state.user = payload
        except Exception as e:
            logger.error(f"JWT Decode Error: {e}")
            return custom_json_response(success=False, code=401, error="Unauthorized")

        return await call_next(request)