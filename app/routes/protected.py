from fastapi import APIRouter, Depends
from app.auth.dependencies import (
    get_current_active_user, 
    require_permission, 
    require_role
)
from app.models.user import User

router = APIRouter(tags=["protected"])


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """Get user profile - requires authentication"""
    return {
        "message": "Profile data",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "provider": current_user.provider,
            "roles": [role.name for role in current_user.roles]
        }
    }


@router.get("/posts")
async def read_posts(current_user: User = Depends(require_permission("posts:read"))):
    """Read posts - requires posts:read permission"""
    return {
        "message": "Here are the posts",
        "posts": [
            {"id": 1, "title": "Post 1", "content": "Content 1"},
            {"id": 2, "title": "Post 2", "content": "Content 2"},
        ],
        "user": current_user.username
    }


@router.post("/posts/create")
async def create_post(current_user: User = Depends(require_permission("posts:create"))):
    """Create post - requires posts:create permission"""
    return {
        "message": "Post created successfully",
        "post": {"id": 3, "title": "New Post", "content": "New Content"},
        "created_by": current_user.username
    }


@router.get("/settings")
async def access_settings(current_user: User = Depends(require_permission("settings:read"))):
    """Access settings - requires settings:read permission"""
    return {
        "message": "System settings",
        "settings": {
            "theme": "dark",
            "language": "pt-BR",
            "notifications": True
        },
        "accessed_by": current_user.username
    } 