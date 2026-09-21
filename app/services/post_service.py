import json
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.singleflight import get_default_sync_singleflight
from app.db.redis import get_redis
from app.helpers.log import logger
from app.models.posts import Post
from app.repository.post_repo import PostRepository


class PostService(object):
    def __init__(self, db_session: Session):
        self.post_repo = PostRepository(db_session)
        self.redis_client = get_redis()
        self.sync_flight = get_default_sync_singleflight()

    def get_post(self, post_id: int):
        def _fetch_db():
            post = self.post_repo.get_post_by_id(post_id)
            if not post:
                return None
            return post.__to_dict__()

        # Áp dụng Distributed Singleflight: 
        # Nếu có 100,000 requests đồng thời ở nhiều Pod, chỉ 1 request gọi _fetch_db và set cache
        res = self.sync_flight.execute(
            key=f"post:{post_id}",
            fetch_fn=_fetch_db,
            cache_ttl=30,
        )
        if res is None:
            raise HTTPException(status_code=404, detail="Post not found")
        return res

    def create_post(self, request: dict):
        title = request.get("title")
        content = request.get("content")
        category_id = request.get("category_id")
        if not category_id:
            raise ValueError("Category ID is required")
        
        if not title:
            raise ValueError("Title is required")
        if not content:
            raise ValueError("Content is required")
        
        post = Post(title=title, content=content, category_id=category_id)
        return self.post_repo.create_post(post)

    def get_posts(self, request):
        page = int(request.get("page", 1))
        limit = int(request.get("limit", 10))
        title = request.get("title")
        category_id = request.get("category_id")

        if page < 1 or limit < 1:
            logger.error("Page and limit must be greater than 0")
            return []

        key_ = f"posts:{page}:{limit}:{title}:{category_id}"

        def _fetch_posts():
            posts = self.post_repo.get_posts(page, limit, title, category_id)
            if not posts:
                return []
            return [post.__to_dict__() for post in posts]

        return self.sync_flight.execute(key=key_, fetch_fn=_fetch_posts, cache_ttl=20)