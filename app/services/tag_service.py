import json
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.redis import get_redis
from app.repository.base_repo import BaseRepository

class TagService(object):
    def __init__(self, db_session: Session):
        self.base_repo = BaseRepository(db_session)
        self.redis_client = get_redis()


    def get_tags(self, request: dict):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        key = f"tags:{page}:{limit}"
        res = self.redis_client.get_json(key)
        if res:
            tags = res["tags"]
            count = res["count"]
            return tags, count

        tags, count = self.base_repo.TagRepository.get_tags(page=page, limit=limit)
        cache_value = {
            "tags": jsonable_encoder(tags),
            "count": count
        }
        self.redis_client.set_with_ttl(key, json.dumps(cache_value).encode("utf-8"), 60)
        
        return tags, count
