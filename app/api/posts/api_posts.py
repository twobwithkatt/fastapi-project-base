from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.postgres import get_db
from app.models.posts import Post
from app.services.post_service import PostService


post_router = APIRouter()

def get_post_service(db: Session = Depends(get_db)) -> PostService:
    return PostService(db)

@post_router.get("/{post_id}", tags=["posts"])
def get_post(post_id: int, post_service: PostService = Depends(get_post_service)):
    return post_service.get_post(post_id)


@post_router.post("", tags=["posts"])
def create_post(request: dict, post_service: PostService = Depends(get_post_service)):
    return post_service.create_post(request)


@post_router.get("", tags=["posts"])
def get_posts(request: Request, post_service: PostService = Depends(get_post_service)):
    query_params = request.query_params
    return post_service.get_posts(query_params)


from app.core.singleflight import distributed_singleflight

@post_router.get("/{post_id}/async-singleflight", tags=["posts"])
@distributed_singleflight(key_pattern="post:async:{post_id}", cache_ttl=60)
async def get_post_async_singleflight(post_id: int, db: Session = Depends(get_db)):
    """
    Demo endpoint sử dụng @distributed_singleflight decorator.
    Khi 100,000 request ập vào đồng thời trên nhiều Pod:
    - Pods tự collapse request cục bộ bằng in-memory singleflight
    - Đại diện các Pod tranh chấp Redis Distributed Lock
    - Chỉ 1 request trên toàn bộ hệ thống thực thi query DB bên dưới
    - 99,999 request còn lại nhận data từ cache qua Redis Pub/Sub thông báo
    """
    post_service = PostService(db)
    post = post_service.post_repo.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post.__to_dict__()