"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import logging
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.services.robinhood_service import RobinhoodService
from app.schemas.common import DataResponse, ErrorResponse
from app.core.security import create_access_token, ensure_demo_user_exists, get_password_hash
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str
    mfa_code: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response model"""
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user_info: Optional[dict] = None



def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()


async def get_or_create_user_for_robinhood_login(
    db: AsyncSession,
    username: str,
    rh_service: RobinhoodService
) -> User:
    """Find or create user for Robinhood login using Robinhood's unique user ID"""
    try:
        # Get Robinhood user ID from the service
        robinhood_user_id = rh_service.get_robinhood_user_id()

        if robinhood_user_id:
            # Try to use Robinhood's user ID as UUID
            try:
                # If it's already a valid UUID, use it
                user_uuid = uuid.UUID(robinhood_user_id)
            except ValueError:
                # If not a valid UUID, create a deterministic UUID from it
                import hashlib
                hash_obj = hashlib.md5(robinhood_user_id.encode())
                user_uuid = uuid.UUID(hash_obj.hexdigest())

            # Try to find existing user by this ID
            stmt = select(User).where(User.id == user_uuid)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                # Update last login
                user.last_login = datetime.utcnow()
                user.robinhood_username = username
                await db.commit()
                logger.info(f"Found existing user: {user.id} for Robinhood user ID: {robinhood_user_id}")
                return user

            # Create new user with Robinhood's user ID
            user = User(
                id=user_uuid,
                email=f"{username}@robinhood.local",
                full_name=f"Robinhood User ({username})",
                robinhood_username=username,
                robinhood_user_id=robinhood_user_id,
                is_active=True,
                last_login=datetime.utcnow()
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

            logger.info(f"Created new user {user.id} for Robinhood user ID: {robinhood_user_id}")
            return user

        # Fallback: If no Robinhood user ID, try to find by username
        stmt = select(User).where(User.robinhood_username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.last_login = datetime.utcnow()
            await db.commit()
            logger.info(f"Found existing user by username: {user.id} for Robinhood username: {username}")
            return user

        # Create new user with generated UUID (fallback when no Robinhood user ID)
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"{username}@robinhood.local",
            full_name=f"Robinhood User ({username})",
            robinhood_username=username,
            is_active=True,
            last_login=datetime.utcnow()
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.warning(f"Created new user {user.id} without Robinhood user ID for username: {username}")
        return user

    except Exception as e:
        logger.error(f"Error getting/creating user for Robinhood login: {str(e)}")
        await db.rollback()
        raise


@router.post(
    "/robinhood/login",
    response_model=LoginResponse,
    responses={
        200: {"description": "Robinhood login successful with JWT token"},
        401: {"description": "Authentication failed", "model": ErrorResponse},
        400: {"description": "Invalid request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def robinhood_login(
    request: LoginRequest,
    rh_service: RobinhoodService = Depends(get_robinhood_service),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate with Robinhood and return JWT token"""
    try:
        # Validate input
        if not request.username or not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required"
            )
        
        # Attempt authentication - now returns detailed response dict
        auth_result = await rh_service.authenticate(
            username=request.username,
            password=request.password,
            mfa_code=request.mfa_code
        )
        
        # Handle the response
        if auth_result["success"]:
            # Find or create user in our database
            user = await get_or_create_user_for_robinhood_login(
                db=db, 
                username=request.username,
                rh_service=rh_service
            )
            
            # Create JWT token with user ID
            access_token = create_access_token(subject=str(user.id))
            
            # Update last login time
            user.last_login = datetime.utcnow()
            await db.commit()
            
            return LoginResponse(
                success=True,
                message=auth_result["message"],
                access_token=access_token,
                token_type="bearer",
                user_info={
                    "user_id": str(user.id),
                    "username": request.username,
                    "email": user.email
                }
            )
        else:
            # Authentication failed
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=auth_result["message"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Robinhood login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )



@router.post(
    "/logout",
    response_model=DataResponse,
    responses={
        200: {"description": "Logout successful"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def logout(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Logout from Robinhood"""
    try:
        logout_result = await rh_service.logout()
        
        return DataResponse(
            data=logout_result
        )
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )


@router.get(
    "/status",
    response_model=DataResponse,
    responses={
        200: {"description": "Authentication status retrieved"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_auth_status(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get current authentication status"""
    try:
        # Use the new session verification method
        authenticated = await rh_service.is_logged_in()
        username = rh_service.get_username()
        
        return DataResponse(
            data={
                "authenticated": authenticated,
                "username": username,
                "message": "Authenticated with Robinhood" if authenticated else "Not authenticated"
            }
        )
        
    except Exception as e:
        logger.error(f"Auth status check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error checking authentication status"
        )


@router.get(
    "/test-connectivity",
    response_model=DataResponse,
    responses={
        200: {"description": "Connectivity test result"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def test_connectivity(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Test connectivity to Robinhood API"""
    try:
        is_connected = await rh_service.test_connectivity()
        
        return DataResponse(
            data={
                "connected": is_connected,
                "message": "Can reach Robinhood API" if is_connected else "Cannot reach Robinhood API"
            }
        )
        
    except Exception as e:
        logger.error(f"Connectivity test error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during connectivity test"
        )