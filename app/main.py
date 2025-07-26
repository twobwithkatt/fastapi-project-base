from contextlib import asynccontextmanager
import os
import uvicorn
from fastapi import FastAPI
from app.api.route.route import router
from app.core.config import settings
from app.core.middleware.jwt import JWTAuthMiddleware
from app.db.postgres import SessionLocal
from app.services.init_data_service import InitDataService
from app.helpers.log import logger
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with SessionLocal() as db:
            init_service = InitDataService(db)
            init_service.init_all()
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise RuntimeError("❌ App startup failed, exiting.") from e

    yield
    db.close()


def init_app() -> FastAPI:
    api_app = FastAPI(lifespan=lifespan)   
    api_app.include_router(router, prefix="/api")
    # api_app.add_middleware(JWTAuthMiddleware, exclude_paths=["/api/auth/login", "/api/auth/register"])
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust this to your needs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return api_app

app = init_app()

if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)