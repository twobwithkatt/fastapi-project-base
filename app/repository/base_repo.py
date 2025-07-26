from sqlalchemy.orm import Session

from app.repository.category_repo import CategoryRepository
from app.repository.post_repo import PostRepository
from app.repository.posts_tags_repo import PostsTagsRepository
from app.repository.tag_repo import TagRepository
from app.repository.user_repo import UserRepository

class BaseRepository:
    def __init__(self, session: Session):
        self.PostRepository = PostRepository(session)
        self.CategoryRepository = CategoryRepository(session)
        self.TagRepository = TagRepository(session)
        self.PostsTagsRepository = PostsTagsRepository(session)
        self.UserRepository = UserRepository(session)