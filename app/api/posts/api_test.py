from fastapi import APIRouter, Depends, Request
from fastapi import Depends
from app.services.auth_service import AuthService

test_router = APIRouter()

@test_router.get("", tags=["test"])
def test():
    return {"data": "OK!"}


@test_router.get("/gen-token", tags=["test"])
def gen_token(auth_service: AuthService = Depends(AuthService)):
    token = auth_service.create_token({"sub": "test_user"})
    return {"token": token}


@test_router.get("/decode-token", tags=["test"])
def decode_token(request: Request, auth_service: AuthService = Depends(AuthService)):
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = auth_service.decode_token(token)
        return {"payload": payload}
    except Exception as e:
        return {"error": str(e)}