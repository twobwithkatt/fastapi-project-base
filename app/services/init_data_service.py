from sqlalchemy.orm import Session
from app.models.user import User
from app.services.auth_service import AuthService
from app.helpers.log import logger
from app.core.config import settings


class InitDataService:
    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthService()

    def create_admin_user(self):
        admin = self.db.query(User).filter(User.username == "admin").first()
        if admin:
            logger.info("ℹ️ Admin user already exists.")
            return

        new_admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=self.auth_service.get_password_hash(settings.ADMIN_PASSWORD),
            display_name="Admin User",
        )
        
        self.db.add(new_admin)
        self.db.commit()
        logger.info("✅ Admin user created.")

    def seed_categories(self):
        logger.info("📦 Seed categories...")

    def init_all(self):
        self.create_admin_user()
        self.seed_categories()