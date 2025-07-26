from sqlalchemy.orm import Session

from app.models.posts import Post
from app.models.posts_tags import PostsTags
from app.models.tags import Tag

class PostsTagsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    
    def create_bulk(self, post_tags: list):
        self.db_session.bulk_save_objects(post_tags)
        self.db_session.commit()
        self.db_session.flush()
        return post_tags
    
    
    def delete_by_post_id(self, post_id: int):
        self.db_session.query(PostsTags).filter(PostsTags.post_id == post_id).delete(synchronize_session=False)
        self.db_session.commit()
        

    def get_tags_by_post_id(self, post_id: int):
        query = (
            self.db_session.query(Tag)
            .join(PostsTags, PostsTags.tag_id == Tag.id)
            .filter(PostsTags.post_id == post_id)
        )
        return query.all()
        
    
    def get_posts_by_tag_id(self, tag_id: int, limit: int, page: int):
        offset = (page - 1) * limit
        
        query = (
            self.db_session.query(Post)
            .outerjoin(PostsTags, Post.id == PostsTags.post_id)
            .outerjoin(Tag, PostsTags.tag_id == Tag.id)
            .filter(Tag.id == tag_id)
            .limit(limit)
            .offset(offset)
        )
        
        count = query.count()
        
        query = query.offset(offset).limit(limit)   
        posts = query.all()
        return posts, count
        
    
    def get_post_ids_by_tag_id(self, tag_id: int):
        query = (
            self.db_session.query(PostsTags.post_id)
            .join(Tag, PostsTags.tag_id == Tag.id)
            .filter(Tag.id == tag_id)
        )
        return [post_tag.post_id for post_tag in query.all()]