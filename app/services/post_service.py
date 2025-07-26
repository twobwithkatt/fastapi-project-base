from fastapi import HTTPException
import json

from fastapi.encoders import jsonable_encoder
from app.db.postgres import get_db
from app.db.redis import get_redis
from app.models.posts import Post, PostOut
from app.models.posts_tags import PostsTags
from app.models.tags import Tag
from app.repository.base_repo import BaseRepository
from app.repository.category_repo import CategoryRepository
from sqlalchemy.orm import Session
from app.helpers.log import logger


class PostService(object):
    def __init__(self, db_session: Session):
        self.base_repo = BaseRepository(db_session)
        self.redis_client = get_redis()

    def get_post(self, post_id: int):
        key = f"post:{post_id}"
        res = self.redis_client.get_json(key)
        if res:
            return res

        post = self.base_repo.PostRepository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        cat = self.base_repo.CategoryRepository.get_category_by_id(post.category_id)
        post.category = cat

        encoded = jsonable_encoder(post)
        self.redis_client.set_with_ttl(key, json.dumps(encoded).encode('utf-8'), 30)
        return post
    
    def create_post(self, request: dict):
        title = request.get("title")
        content = request.get("content")
        category_id = request.get("category_id")
        tags = request.get("tags", [])
        if not category_id:
            raise HTTPException(status_code=400, detail="Category ID is required")
        
        if not title:
            raise HTTPException(status_code=400, detail="Title is required")
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        if tags:
            if not all(isinstance(tag, str) for tag in tags):
                raise HTTPException(status_code=400, detail="Tags must be a list of strings")

            tag_names = set(tag.strip() for tag in tags if tag.strip())
            if not tag_names:
                tags = []
            else:
                existing_tags = self.base_repo.TagRepository.get_tags_by_names(list(tag_names))
                existing_tag_names = set(tag.name for tag in existing_tags)

                new_tag_names = tag_names - existing_tag_names
                new_tags = [Tag(name=name) for name in new_tag_names]

                if new_tags:
                    self.base_repo.TagRepository.create_tag_bulk(new_tags)
                    existing_tags.extend(new_tags)

                tags = existing_tags
                
        category = self.base_repo.CategoryRepository.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=400, detail="Category invalid")
        
        post = Post(title=title, content=content, category_id=category_id)
        created_post = self.base_repo.PostRepository.create_post(post)
        
        self.base_repo.PostsTagsRepository.delete_by_post_id(created_post.id)
        self.base_repo.PostsTagsRepository.create_bulk([
            PostsTags(post_id=created_post.id, tag_id=tag.id)
            for tag in tags
        ])

        return created_post

    
    def get_posts(self, request):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        title = request.query_params.get("title")
        category_id = request.query_params.get("category_id")

        key_ = f"posts:{page}:{limit}:{title}:{category_id}"
        cached_posts = self.redis_client.get_json(key_)
        if cached_posts:
            posts = cached_posts["posts"]
            count = cached_posts["count"]
            return posts, count
        
        if not isinstance(page, int) or not isinstance(limit, int):
            raise ValueError("Page and limit must be integers")
     
        posts, count = self.base_repo.PostRepository.get_posts(page, limit, title, category_id)

        cat_map = {}
        
        # fetch categories for the posts
        cat_ids = [post.category_id for post in posts if post.category_id]
        categories = self.base_repo.CategoryRepository.get_categories_by_ids(cat_ids)
        for cat in categories:
            cat_map[cat.id] = cat
        
        for post in posts:
            post.category = cat_map.get(post.category_id)
            
        # fetch tags for the posts
        for post in posts:
            post_tags = self.base_repo.PostsTagsRepository.get_tags_by_post_id(post.id)
            post.tags = post_tags

        cache_value = {
            "posts": jsonable_encoder(posts),
            "count": count
        }
        self.redis_client.set_with_ttl(key_, json.dumps(cache_value).encode("utf-8"), 60)
        
        return posts, count
    
    
    def update_post(self, post_id: int, request: dict):
        post = self.base_repo.PostRepository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        title = request.get("title")
        content = request.get("content")
        category_id = request.get("category_id")

        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        if category_id is not None:
            post.category_id = category_id

        updated_post = self.base_repo.PostRepository.update_by_id(post)
        if not updated_post:
            raise HTTPException(status_code=500, detail="Failed to update post")
    
        key = f"post:{post_id}"
        self.redis_client.delete(key)
        return updated_post
    

    def delete_post(self, post_id: int):
        post = self.base_repo.PostRepository.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        self.base_repo.PostRepository.delete_by_id(post)

        key = f"post:{post_id}"
        self.redis_client.delete(key)
        return None
    
    
    def get_posts_by_tag_id(self, tag_id: int, page: int, limit: int):
        if not tag_id:
            raise HTTPException(status_code=400, detail="Tag ID is required")

        key = f"posts_by_tag:{tag_id}:{page}:{limit}"
        cached_posts = self.redis_client.get_json(key)
        if cached_posts:
            posts = cached_posts["posts"]
            count = cached_posts["count"]
            return posts, count

        posts, count = self.base_repo.PostsTagsRepository.get_posts_by_tag_id(tag_id, limit, page)
        if not posts:
            raise HTTPException(status_code=404, detail="No posts found for this tag")
        
        cat_map = {}
        cat_ids = [post.category_id for post in posts]
        categories = self.base_repo.CategoryRepository.get_categories_by_ids(cat_ids)
        for cat in categories:
            cat_map[cat.id] = cat
            
        for post in posts:
            post.category = cat_map.get(post.category_id)
        
        cached_value = {
            "posts": jsonable_encoder(posts),
            "count": count
        }
        
        self.redis_client.set_with_ttl(key, json.dumps(cached_value).encode("utf-8"), 60)

        return posts, count


    def get_posts_archive(self):
        key = "post_archive"
        cached_archive = self.redis_client.get_json(key)
        if cached_archive:
            return cached_archive
        
        posts = self.base_repo.PostRepository.get_post_archive()
        archive = {}
        
        for post in posts:
            year = post.created_at.year
            if year not in archive:
                archive[year] = []
            archive[year].append({
                "id": post.id,
                "title": post.title,
                "created_at": post.created_at.isoformat()
            })
            
        self.redis_client.set_with_ttl(key, json.dumps(archive).encode("utf-8"), 60)
        return archive
