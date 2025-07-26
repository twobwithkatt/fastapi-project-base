from fastapi import APIRouter, Depends, HTTPException
from requests import Session

from app.db.postgres import get_db
from app.helpers.response import CustomResponse, error_response, internal_error_response, ok_response
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.helpers.log import logger


auth_router = APIRouter()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@auth_router.post("/login", tags=["auth"], response_model=CustomResponse[dict])
def login(request: dict, user_service: UserService = Depends(get_user_service)):
    try:
        token = user_service.login(request)
        return ok_response(code=200, data={"token": token})

    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)
    

@auth_router.post("/register", tags=["auth"], response_model=CustomResponse[int])
def register(request: dict, user_service: UserService = Depends(get_user_service)):
    try:
        user_id = user_service.register(request)
        return ok_response(user_id, code=201)

    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)