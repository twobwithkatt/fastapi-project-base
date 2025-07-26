from app.models.categories import Category
from sqlalchemy.orm import Session


class CategoryRepository:
    def __init__(self, session: Session):
        self.session = session
        
    
    def get_category_by_id(self, category_id: int):
        return self.session.query(Category).filter(Category.id == category_id).first()
    
    
    def create_category(self, category):
        self.session.add(category)
        self.session.commit()
        return category
    
    
    def get_categories_by_ids(self, category_ids: list):
        return self.session.query(Category).filter(Category.id.in_(category_ids)).all()
    
    
    def get_categories(self, page: int = 1, limit: int = 10, name: str = None):
        query = self.session.query(Category)
        
        if name:
            query = query.filter(Category.name.ilike(f"%{name}%"))
        
        query = query.order_by(Category.updated_at.desc())
        offset = (page - 1) * limit
        
        count = query.count()
        return query.offset(offset).limit(limit).all(), count