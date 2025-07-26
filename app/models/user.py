from sqlalchemy import Column, String, String
from pydantic import BaseModel
from app.models.base import BareBaseModel


class User(BareBaseModel):
    __tablename__ = 'users'

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    display_name = Column(String(100), nullable=True)
    

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    display_name: str | None = None

    class Config:
        from_attributes = True
