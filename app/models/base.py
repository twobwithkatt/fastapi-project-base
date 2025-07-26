import json
from typing import Generic, TypeVar
from pydantic import BaseModel
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime

@as_declarative()
class ORMBase:
    __abstract__ = True
    __name__: str

    def __to_dict__(self, exclude: set = None):
        result = {}
        exclude = exclude or set()
        
        for c in self.__table__.columns:
            if c.name in exclude:
                continue
            value = getattr(self, c.name)
            if isinstance(value, datetime):
                result[c.name] = value.isoformat()
            else:
                result[c.name] = value
        return result
    
    def __to_json_byte__(self):
        return json.dumps(self.__to_dict__(), default=str).encode('utf-8')

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class BareBaseModel(ORMBase):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, index=True)
    

T = TypeVar("T")
    
class ListOut(BaseModel, Generic[T]):
    items: list[T]
    total: int

    class Config:
        from_attributes = True