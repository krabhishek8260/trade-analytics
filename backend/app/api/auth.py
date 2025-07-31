"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.robinhood_service import RobinhoodService
from app.schemas.common import DataResponse, ErrorResponse

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
    user_info: Optional[dict] = None



def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()


@router.post(
    "/robinhood/login",
    response_model=LoginResponse,
    responses={
        200: {"description": "Robinhood login successful or requires MFA"},
        401: {"description": "Authentication failed", "model": ErrorResponse},
        400: {"description": "Invalid request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def robinhood_login(
    request: LoginRequest,
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Authenticate with Robinhood (frontend-specific endpoint)"""
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
            return LoginResponse(
                success=True,
                message=auth_result["message"],
                user_info={"username": request.username}
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