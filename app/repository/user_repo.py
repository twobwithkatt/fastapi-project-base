from sqlalchemy.orm import Session
from app.models.user import User


class UserRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    
    def get_user_by_id(self, user_id: int):
        return self.db_session.query(User).filter(User.id == user_id).first()
    
    
    def get_user_by_username(self, username: str):
        return self.db_session.query(User).filter(User.username == username).first()
    
    
    def create_user(self, user: User):
        self.db_session.add(user)
        self.db_session.commit()
        return user