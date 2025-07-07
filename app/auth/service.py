from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from app.models.schemas import UserCreate
from app.auth.utils import verify_password, get_password_hash


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not user.hashed_password:  # OAuth user without password
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, user_create: UserCreate) -> User:
        """Create new user"""
        hashed_password = None
        if user_create.password:
            hashed_password = get_password_hash(user_create.password)
        
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=user_create.is_active,
            provider=user_create.provider or "basic",
            provider_id=user_create.provider_id
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_or_create_oauth_user(self, email: str, full_name: str, provider: str, provider_id: str) -> User:
        """Get existing OAuth user or create new one"""
        # Try to find user by provider_id and provider
        user = self.db.query(User).filter(
            User.provider_id == provider_id,
            User.provider == provider
        ).first()
        
        if user:
            return user
        
        # Try to find user by email
        user = self.get_user_by_email(email)
        if user:
            # Update existing user with OAuth info
            user.provider = provider
            user.provider_id = provider_id
            if not user.full_name and full_name:
                user.full_name = full_name
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # Create new user
        username = email.split("@")[0]  # Use email prefix as username
        # Ensure username is unique
        counter = 1
        original_username = username
        while self.get_user_by_username(username):
            username = f"{original_username}{counter}"
            counter += 1
        
        user_create = UserCreate(
            username=username,
            email=email,
            full_name=full_name,
            provider=provider,
            provider_id=provider_id
        )
        
        return self.create_user(user_create) 