from sqlalchemy.orm import Session

from app.models.tags import Tag

class TagRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_tag_by_id(self, tag_id: int):
        return self.db_session.query(Tag).filter(Tag.id == tag_id).first()


    def create_tag_bulk(self, tags: list[Tag]):
        self.db_session.add_all(tags)
        self.db_session.commit()
        return tags
    
    
    def get_tags_by_names(self, names: list[str]):
        return self.db_session.query(Tag).filter(Tag.name.in_(names)).all()
    
    
    def get_tags(self, page: int = 1, limit: int = 10):
        query = self.db_session.query(Tag)
        
        offset = (page - 1) * limit
        query = query.order_by(Tag.updated_at.desc())
        
        count = query.count()
        return query.offset(offset).limit(limit).all(), count
    
    
    def get_tags_by_ids(self, tag_ids: list[int]):
        return self.db_session.query(Tag).filter(Tag.id.in_(tag_ids)).all()