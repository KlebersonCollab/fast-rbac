from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from urllib.parse import urlencode

from app.database.base import get_db
from app.auth.oauth import OAuthProvider, authenticate_oauth_user
from app.auth.utils import create_access_token
from app.models.schemas import Token
from app.config.settings import settings

router = APIRouter(tags=["oauth"])


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login with provider"""
    try:
        oauth_provider = OAuthProvider(provider)
        redirect_uri = str(request.url_for('oauth_callback', provider=provider))
        authorization_url = await oauth_provider.get_authorization_url(request, redirect_uri)
        return RedirectResponse(authorization_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback and create user session"""
    try:
        user = await authenticate_oauth_user(provider, request, db)
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        # In production, you might want to redirect to your frontend app
        frontend_url = "http://localhost:3000"  # Adjust as needed
        params = urlencode({
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        })
        
        return RedirectResponse(f"{frontend_url}/auth/callback?{params}")
        
    except Exception as e:
        # Redirect to frontend with error
        frontend_url = "http://localhost:3000"
        params = urlencode({"error": str(e)})
        return RedirectResponse(f"{frontend_url}/auth/error?{params}")


@router.post("/{provider}/token", response_model=Token)
async def oauth_token(provider: str, request: Request, db: Session = Depends(get_db)):
    """Get token after OAuth authentication (for API usage)"""
    try:
        user = await authenticate_oauth_user(provider, request, db)
        
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers")
async def get_oauth_providers():
    """Get list of configured OAuth providers"""
    providers = []
    
    if settings.google_client_id:
        providers.append({
            "name": "google",
            "display_name": "Google",
            "login_url": "/oauth/google/login"
        })
    
    if settings.microsoft_client_id:
        providers.append({
            "name": "microsoft", 
            "display_name": "Microsoft",
            "login_url": "/oauth/microsoft/login"
        })
    
    if settings.github_client_id:
        providers.append({
            "name": "github",
            "display_name": "GitHub", 
            "login_url": "/oauth/github/login"
        })
    
    return {"providers": providers} 