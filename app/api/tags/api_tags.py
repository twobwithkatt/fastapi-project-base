from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.helpers.response import CustomResponse, error_response, internal_error_response, ok_response
from app.models.base import ListOut
from app.models.tags import Tag, TagOut
from app.services.tag_service import TagService
from app.helpers.log import logger

tag_router = APIRouter()

def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


@tag_router.get("", tags=["tags"], response_model=CustomResponse[ListOut[TagOut]])
def get_tags(request: Request, tag_service: TagService = Depends(get_tag_service)):
    try:
        tags, total = tag_service.get_tags(request)
        tags_out = [TagOut.model_validate(tag) for tag in tags]
        return ok_response(data=ListOut(items=tags_out, total=total))

    except HTTPException as e:
        return error_response(message=e.detail, code=e.status_code)

    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(code=500)