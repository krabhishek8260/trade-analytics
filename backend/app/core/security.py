"""
Security utilities for authentication and authorization
"""

from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError as e:
        logger.error(f"JWT error: {e}")
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_credentials_exception() -> HTTPException:
    """Create credentials exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Demo user ID for testing when no auth is implemented
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> uuid.UUID:
    """
    Get current authenticated user ID from JWT token.
    
    Args:
        authorization: Bearer token from Authorization header
        
    Returns:
        UUID of the current user
        
    Raises:
        HTTPException: If authentication fails
    """
    
    # Check if we have an authorization header
    if not authorization:
        # No authorization header - use demo user for development
        logger.debug(f"No authorization header, using demo user ID: {DEMO_USER_ID}")
        return DEMO_USER_ID
    
    # Validate the JWT token
    if not authorization.startswith("Bearer "):
        raise create_credentials_exception()
    
    token = authorization.split(" ")[1]
    user_id_str = verify_token(token)
    
    if not user_id_str:
        raise create_credentials_exception()
    
    try:
        user_id = uuid.UUID(user_id_str)
        logger.debug(f"Authenticated user from JWT: {user_id}")
        return user_id
    except ValueError:
        raise create_credentials_exception()


async def ensure_demo_user_exists(db: AsyncSession) -> None:
    """
    Ensure user exists in database for development/testing.
    This will create users for any user_ids found in the orders data.
    """
    try:
        from app.models.user import User
        from sqlalchemy import text
        
        # Find all unique user IDs in the orders data
        result = await db.execute(text("SELECT DISTINCT user_id FROM options_orders"))
        user_ids = result.scalars().all()
        
        for user_id_str in user_ids:
            user_id = uuid.UUID(str(user_id_str))
            
            # Check if user exists
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                # Create user
                if user_id == DEMO_USER_ID:
                    email = "demo@tradeanalytics.local"
                    full_name = "Demo User"
                    rh_username = "demo_user"
                else:
                    email = f"user_{str(user_id_str)}@robinhood.local"
                    full_name = "Robinhood User"
                    rh_username = f"rh_user_{str(user_id_str)[:8]}"
                
                user = User(
                    id=user_id,
                    email=email,
                    full_name=full_name,
                    is_active=True,
                    robinhood_username=rh_username
                )
                db.add(user)
                logger.info(f"Created user with ID: {user_id}")
        
        # Always ensure demo user exists as fallback
        stmt = select(User).where(User.id == DEMO_USER_ID)
        result = await db.execute(stmt)
        demo_user = result.scalar_one_or_none()
        
        if not demo_user:
            demo_user = User(
                id=DEMO_USER_ID,
                email="demo@tradeanalytics.local",
                full_name="Demo User",
                is_active=True,
                robinhood_username="demo_user"
            )
            db.add(demo_user)
            logger.info(f"Created demo user with ID: {DEMO_USER_ID}")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error ensuring users exist: {str(e)}")
        # Don't raise - this is non-critical for testing