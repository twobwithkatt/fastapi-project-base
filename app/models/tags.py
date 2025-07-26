from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from app.models.base import BareBaseModel


class Tag(BareBaseModel):
    __tablename__ = "tags"

    name = Column(String, index=True)


class TagOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
        

class TagListOut(BaseModel):
    tags: list[TagOut]
    total: int

    class Config:
        from_attributes = True