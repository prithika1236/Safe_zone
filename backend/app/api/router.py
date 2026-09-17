from fastapi import APIRouter
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.crimes import router as crimes_router
from app.api.help_points import router as help_points_router

api_router = APIRouter(prefix="/api/v1")

# Authentication and user endpoints
api_router.include_router(auth_router)

# Admin management endpoints
api_router.include_router(admin_router)

# Crime data management endpoints
api_router.include_router(crimes_router)

# Safe Help Points endpoints
api_router.include_router(help_points_router)
