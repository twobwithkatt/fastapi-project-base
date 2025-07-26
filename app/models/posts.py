from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime, Integer
from app.models.base import BareBaseModel
from sqlalchemy.orm import relationship

from app.models.categories import Category, CategoryOut
from app.models.tags import TagOut

class Post(BareBaseModel):
    __tablename__ = 'posts'

    title = Column(String(255),index=True, nullable=False)
    content = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)

class PostOut(BaseModel):
    id: int
    title: str
    content: str
    category: CategoryOut
    tags: list[TagOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        

class PostUpdateOut(BaseModel):
    id: int

    class Config:
        from_attributes = True