from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from app.models.base import BareBaseModel

class Category(BareBaseModel):
    __tablename__ = 'categories'

    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        

class CategoryListOut(BaseModel):
    categories: list[CategoryOut]
    total: int

    class Config:
        from_attributes = True