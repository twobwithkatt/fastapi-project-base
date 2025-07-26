from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, Integer
from app.models.base import BareBaseModel


class PostsTags(BareBaseModel):
    __tablename__ = "posts_tags"

    id = None  # loại bỏ id

    post_id = Column(Integer, primary_key=True, index=True, nullable=False)
    tag_id = Column(Integer, primary_key=True, index=True, nullable=False)
