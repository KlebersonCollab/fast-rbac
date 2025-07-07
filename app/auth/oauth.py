from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
import httpx
from typing import Dict, Any

from app.config.settings import settings
from app.auth.service import AuthService

# Initialize OAuth
oauth = OAuth()

# Configure OAuth providers
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

if settings.microsoft_client_id and settings.microsoft_client_secret:
    oauth.register(
        name='microsoft',
        client_id=settings.microsoft_client_id,
        client_secret=settings.microsoft_client_secret,
        authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

if settings.github_client_id and settings.github_client_secret:
    oauth.register(
        name='github',
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        authorize_url='https://github.com/login/oauth/authorize',
        access_token_url='https://github.com/login/oauth/access_token',
        client_kwargs={
            'scope': 'user:email'
        }
    )


class OAuthProvider:
    def __init__(self, name: str):
        self.name = name
        self.client = getattr(oauth, name, None)
        if not self.client:
            raise HTTPException(status_code=400, detail=f"OAuth provider '{name}' not configured")

    async def get_authorization_url(self, request: Request, redirect_uri: str) -> str:
        """Get authorization URL for OAuth flow"""
        return await self.client.authorize_redirect(request, redirect_uri)

    async def get_user_info(self, request: Request) -> Dict[str, Any]:
        """Get user info from OAuth provider"""
        token = await self.client.authorize_access_token(request)
        
        if self.name == 'google':
            user_info = token.get('userinfo')
            if not user_info:
                # Fallback to userinfo endpoint
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        'https://www.googleapis.com/oauth2/v2/userinfo',
                        headers={'Authorization': f"Bearer {token['access_token']}"}
                    )
                    user_info = response.json()
            
            return {
                'email': user_info.get('email'),
                'full_name': user_info.get('name'),
                'provider_id': user_info.get('sub'),
                'provider': 'google'
            }
        
        elif self.name == 'microsoft':
            user_info = token.get('userinfo')
            if not user_info:
                # Fallback to Microsoft Graph API
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        'https://graph.microsoft.com/v1.0/me',
                        headers={'Authorization': f"Bearer {token['access_token']}"}
                    )
                    user_info = response.json()
            
            return {
                'email': user_info.get('mail') or user_info.get('userPrincipalName'),
                'full_name': user_info.get('displayName'),
                'provider_id': user_info.get('id'),
                'provider': 'microsoft'
            }
        
        elif self.name == 'github':
            # Get user info from GitHub API
            async with httpx.AsyncClient() as client:
                # Get user profile
                user_response = await client.get(
                    'https://api.github.com/user',
                    headers={'Authorization': f"Bearer {token['access_token']}"}
                )
                user_info = user_response.json()
                
                # Get user email (if not public)
                email = user_info.get('email')
                if not email:
                    email_response = await client.get(
                        'https://api.github.com/user/emails',
                        headers={'Authorization': f"Bearer {token['access_token']}"}
                    )
                    emails = email_response.json()
                    primary_email = next((e for e in emails if e.get('primary')), None)
                    email = primary_email.get('email') if primary_email else None
                
                return {
                    'email': email,
                    'full_name': user_info.get('name'),
                    'provider_id': str(user_info.get('id')),
                    'provider': 'github'
                }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {self.name}")


async def authenticate_oauth_user(provider_name: str, request: Request, db: Session):
    """Authenticate user with OAuth provider"""
    provider = OAuthProvider(provider_name)
    user_info = await provider.get_user_info(request)
    
    if not user_info.get('email'):
        raise HTTPException(status_code=400, detail="Email not provided by OAuth provider")
    
    auth_service = AuthService(db)
    user = auth_service.get_or_create_oauth_user(
        email=user_info['email'],
        full_name=user_info.get('full_name', ''),
        provider=user_info['provider'],
        provider_id=user_info['provider_id']
    )
    
    return user 