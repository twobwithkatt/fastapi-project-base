from sqlalchemy.orm import Session

from app.models.posts import Post


class PostRepository:
    def __init__(self, session: Session):
        self.session = session

    
    def get_post_by_id(self, post_id: int):
        return self.session.query(Post).filter(Post.id == post_id).first()
    
    def create_post(self, post):
        self.session.add(post)
        self.session.commit()
        return post

    def get_posts(self, page: int, limit: int, title: str = None, category_id: int = None):
        query = self.session.query(Post)
        
        if title:
            query = query.filter(Post.title.ilike(f"%{title}%"))
        
        if category_id:
            query = query.filter(Post.category_id == category_id)

        count = query.count()
    
        query = query.order_by(Post.updated_at.desc())
        offset = (page - 1) * limit

        return query.offset(offset).limit(limit).all(), count
    
    
    def get_posts_count(self, title: str = None, category_id: int = None):
        query = self.session.query(Post)
        
        if title:
            query = query.filter(Post.title.ilike(f"%{title}%"))
        
        if category_id:
            query = query.filter(Post.category_id == category_id)

        return query.count()

    
    def update_by_id(self, post: Post):
        self.session.add(post)
        self.session.commit()
        return post
    
    
    def delete_by_id(self, post: Post):
        self.session.delete(post)
        self.session.commit()
        
    
    def get_posts_by_ids(self, post_ids: list[int], page: int, limit: int):
        query = self.session.query(Post).filter(Post.id.in_(post_ids))
        
        offset = (page - 1) * limit
        count = query.count()
        
        query = query.order_by(Post.updated_at.desc())
        return query.offset(offset).limit(limit).all(), count
    

    def get_post_archive(self):
        query = self.session.query(Post.id, Post.title, Post.created_at)
        query = query.order_by(Post.updated_at.desc())

        return query.all()