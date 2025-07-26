from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.helpers.response import CustomResponse, internal_error_response, ok_response
from app.models.base import ListOut
from app.models.categories import Category, CategoryListOut, CategoryOut
from app.services.category_service import CategoryService
from app.db.postgres import get_db
from app.helpers.log import logger

category_router = APIRouter()

def get_category_service(db: Session = Depends(get_db)):
    return CategoryService(db)


@category_router.get("/{category_id}", tags=["categories"], response_model=CustomResponse[CategoryOut])
def get_category(category_id: int, category_service: CategoryService = Depends(get_category_service)):
    try:
        category = category_service.get_category(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        category_out = CategoryOut.model_validate(category)
        return CustomResponse(success=True, code=200, data=category_out)
    
    except HTTPException as e:
        return CustomResponse(success=False, code=e.status_code, error=e.detail)
    
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return CustomResponse(success=False, code=500, error="Internal Server Error")


@category_router.post("", tags=["categories"], response_model=CustomResponse[int])
def create_category(request: dict, category_service: CategoryService = Depends(get_category_service)):
    try:
        category = category_service.create_category(request)
        return CustomResponse(success=True, code=201, data=category.id)

    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return CustomResponse(success=False, code=500, error="Internal Server Error")
    

@category_router.get("", tags=["categories"], response_model=CustomResponse[ListOut[CategoryOut]])
def get_categories(request: Request, category_service: CategoryService = Depends(get_category_service)):
    try:
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        name = request.query_params.get("name")

        categories, count = category_service.get_categories(page=page, limit=limit, name=name)

        categories_out = [CategoryOut.model_validate(cat) for cat in categories]
        return ok_response(success=True, code=200, data=ListOut(items=categories_out, total=count))

    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        return internal_error_response(success=False, code=500, error="Internal Server Error")