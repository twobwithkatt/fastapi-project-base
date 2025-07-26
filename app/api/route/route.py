from fastapi import APIRouter
from app.api.auth import api_auth
from app.api.categories import api_categories
from app.api.posts import api_posts, api_test
from app.api.tags import api_tags


router = APIRouter()

router.include_router(api_categories.category_router, prefix="/categories", tags=["categories"])
router.include_router(api_posts.post_router, prefix="/posts", tags=["posts"])
router.include_router(api_test.test_router, prefix="/test", tags=["test"])
router.include_router(api_tags.tag_router, prefix="/tags", tags=["tags"])
router.include_router(api_auth.auth_router, prefix="/auth", tags=["auth"])