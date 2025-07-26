from fastapi import HTTPException
from app.core.config import settings
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone


class JwtPayload:
    def __init__(self, sub: str, user: dict):
        self.sub = sub
        self.user = user

    def to_dict(self):
        return {
            "sub": str(self.sub),
            "user": self.user,
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }


class AuthService:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expire = settings.JWT_EXPIRE_MINUTES
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    
    def create_token(self, data: dict) -> str:
        to_encode = data.copy()
        to_encode.update({"exp": datetime.now(timezone.utc) + timedelta(minutes=self.expire)})
        token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return token
    

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise Exception(f"JWT Decode Error: {e}")


    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
    
    
    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)