from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.auth.service import AuthService
from app.auth.utils import create_access_token
from app.config.settings import settings
from app.database.base import get_db
from app.models.schemas import LoginRequest, Token, User, UserRegister

router = APIRouter(tags=["authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_register: UserRegister, db: Session = Depends(get_db)):
    """Register a new user and create a tenant for them."""
    auth_service = AuthService(db)

    # Check for existing user/email first to provide clear errors
    if auth_service.get_user_by_username(user_register.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if auth_service.get_user_by_email(user_register.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    try:
        user = auth_service.create_user_and_tenant(user_register)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration.",
        )


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
    
    # Add user_id and tenant_id to the token payload
    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "tenant_id": user.tenant_id
    }
    
    access_token = create_access_token(
        data=token_data, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return current_user


@router.get("/test-token")
async def test_token(current_user: User = Depends(get_current_active_user)):
    """Test endpoint to verify token"""
    return {"message": f"Hello {current_user.username}!", "user_id": current_user.id}
