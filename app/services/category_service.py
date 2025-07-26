import json
import json
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from app.db.postgres import get_db
from app.db.redis import get_redis
from app.models.categories import Category
from app.repository.base_repo import BaseRepository
from app.repository.category_repo import CategoryRepository


class CategoryService(object):
    def __init__(self, db_session: Session):
        self.base_repo = BaseRepository(db_session)
        self.redis_client = get_redis()
    
    def get_category(self, category_id: int):
        return self.base_repo.CategoryRepository.get_category_by_id(category_id)

    
    def create_category(self, request: dict):
        name = request.get("name")
        description = request.get("description")

        if not name:
            raise HTTPException(status_code=400, detail="Name is required")

        row = Category(name=name, description=description)
        return self.base_repo.CategoryRepository.create_category(row)


    def get_categories(self, page: int = 1, limit: int = 10, name: str = None):
        key = f"categories:{page}:{limit}:{name}"
        res = self.redis_client.get_json(key)
        if res:
            categories = res["categories"]
            count = res["count"]
            return categories, count

        categories, count = self.base_repo.CategoryRepository.get_categories(page=page, limit=limit, name=name)
        cached_value = {
            "categories": jsonable_encoder(categories),
            "count": count
        }
        self.redis_client.set_with_ttl(key, json.dumps(cached_value).encode("utf-8"), 60)
        
        return categories, count