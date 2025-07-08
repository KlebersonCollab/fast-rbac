from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database.base import get_db
from app.auth.service import AuthService
from app.auth.utils import create_access_token
from app.auth.dependencies import get_current_active_user
from app.models.schemas import (
    Token, UserCreate, User, LoginRequest
)
from app.config.settings import settings

router = APIRouter(tags=["authentication"])


@router.post("/register", response_model=User)
async def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    auth_service = AuthService(db)
    
    # Check if user already exists
    if auth_service.get_user_by_username(user_create.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if auth_service.get_user_by_email(user_create.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if not user_create.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for basic registration"
        )
    
    user = auth_service.create_user(user_create)
    return user


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login with username and password"""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return current_user


@router.get("/test-token")
async def test_token(current_user: User = Depends(get_current_active_user)):
    """Test endpoint to verify token"""
    return {"message": f"Hello {current_user.username}!", "user_id": current_user.id} 