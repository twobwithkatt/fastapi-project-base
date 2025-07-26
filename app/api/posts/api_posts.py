from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.params import Query
from sqlalchemy.orm import Session
from app.db.postgres import get_db
from app.helpers.response import CustomResponse, error_response, internal_error_response, ok_response
from app.models.base import ListOut
from app.models.posts import Post, PostOut
from app.services.post_service import PostService
from app.helpers.log import logger


post_router = APIRouter()

def get_post_service(db: Session = Depends(get_db)) -> PostService:
    return PostService(db)

@post_router.get("/{post_id:int}", tags=["posts"], response_model=CustomResponse[PostOut])
def get_post(post_id: int, post_service: PostService = Depends(get_post_service)):
    try:
        post = post_service.get_post(post_id)
        post_out = PostOut.model_validate(post)
        return ok_response(data=post_out)
    
    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)


@post_router.post("", tags=["posts"], response_model=CustomResponse[int])
def create_post(request: dict, post_service: PostService = Depends(get_post_service)):
    try:
        post = post_service.create_post(request)
        return ok_response(data=post.id)
    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)


@post_router.get("", tags=["posts"], response_model=CustomResponse[ListOut[PostOut]])
def get_posts(request: Request, post_service: PostService = Depends(get_post_service)):
    try:
        posts, count = post_service.get_posts(request)
        posts_out = [PostOut.model_validate(post) for post in posts]
        return ok_response(data=ListOut[PostOut](items=posts_out, total=count))
    
    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)


@post_router.put("/{post_id}", tags=["posts"], response_model=CustomResponse[int])
def update_post(post_id: int, request: dict, post_service: PostService = Depends(get_post_service)):
    try:
        updated_post = post_service.update_post(post_id, request)
        return ok_response(data=updated_post.id)
    
    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)
    

@post_router.delete("/{post_id}", tags=["posts"], response_model=CustomResponse[None])
def delete_post(post_id: int, post_service: PostService = Depends(get_post_service)):
    try:
        post_service.delete_post(post_id)
        return ok_response(data=None)
    
    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)
    

@post_router.get("/tags/{tag_id}", tags=["posts"], response_model=CustomResponse[ListOut[PostOut]])
def get_posts_by_tag_id(tag_id: int, 
                        page: int = Query(1),
                        limit: int = Query(10),
                        post_service: PostService = Depends(get_post_service)):
    try:
        posts, count = post_service.get_posts_by_tag_id(tag_id, page, limit)
        post_outs = [PostOut.model_validate(post) for post in posts]
        return ok_response(data=ListOut[PostOut](items=post_outs, total=count))

    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)


@post_router.get("/archive", tags=["posts"], response_model=CustomResponse[dict])
def get_posts_archive(post_service: PostService = Depends(get_post_service)):
    try:
        posts = post_service.get_posts_archive()
        return ok_response(data=posts)

    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)