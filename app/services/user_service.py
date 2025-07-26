from fastapi import HTTPException
from app.db.redis import get_redis
from app.models.user import User
from app.repository.base_repo import BaseRepository
from app.services.auth_service import AuthService, JwtPayload
from sqlalchemy.orm import Session
from app.helpers.validation import validate_email, validate_password, validate_username


class UserService:
    def __init__(self, db_session: Session):
        self.base_repo = BaseRepository(db_session)
        self.redis_client = get_redis()
        self.auth_service = AuthService()
    
    
    def login(self, request: dict):
        username = request.get("username")
        password = request.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        user = self.base_repo.UserRepository.get_user_by_username(username)
        if not user or not self.auth_service.verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        payload = JwtPayload(
            sub=user.id,
            user=user.__to_dict__(exclude={"password_hash", "created_at", "updated_at", "email"})
        )

        token = self.auth_service.create_token(data=payload.to_dict())
        return token
        
        
    def register(self, request: dict):
        email = request.get("email")
        username = request.get("username")
        password = request.get("password")
        display_name = request.get("display_name", username)
        
        if not email or not username or not password:
            raise HTTPException(status_code=400, detail="Email, username, and password are required")

        if not validate_email(email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        if not validate_password(password):
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long and contain letters and numbers")
        if not validate_username(username):
            raise HTTPException(status_code=400, detail="Username must be alphanumeric and between 3-30 characters long")

        existing_user = self.base_repo.UserRepository.get_user_by_username(username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        hashed_password = self.auth_service.get_password_hash(password)
        
        new_user = User(
            email=email,
            username=username,
            password_hash=hashed_password,
            display_name=display_name
        )

        user = self.base_repo.UserRepository.create_user(new_user)

        return user.id