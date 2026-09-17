from fastapi import APIRouter
from app.api.admin import router as admin_router
from app.api.assignments import admin_router as admin_assignment_router
from app.api.assignments import police_router as police_assignment_router
from app.api.auth import router as auth_router
from app.api.crimes import router as crimes_router
from app.api.help_points import router as help_points_router
from app.api.optimization import router as optimization_router

api_router = APIRouter(prefix="/api/v1")

# Authentication and user endpoints
api_router.include_router(auth_router)

# Admin management endpoints
api_router.include_router(admin_router)

# Crime data management endpoints
api_router.include_router(crimes_router)

# Safe Help Points endpoints
api_router.include_router(help_points_router)

# Admin PRP Optimization endpoints
api_router.include_router(optimization_router)

# Patrol Assignment endpoints
api_router.include_router(admin_assignment_router)
api_router.include_router(police_assignment_router)
