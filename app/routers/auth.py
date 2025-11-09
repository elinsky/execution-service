"""Auth router - API endpoints for authentication."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.database import get_database
from app.models.user import User, UserCreate
from app.services.auth_service import AuthService
from app.utils.auth import verify_access_token
from jose import JWTError


router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    """Login request model."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db=Depends(get_database)):
    """
    Register a new user.

    Args:
        user: User registration data
        db: Database connection

    Returns:
        Created user object

    Raises:
        HTTPException: If email is already registered (400)
    """
    service = AuthService(db)

    try:
        created_user = await service.register_user(
            email=user.email,
            password=user.password,
            name=user.name,
        )
        return created_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login(login_req: LoginRequest, db=Depends(get_database)):
    """
    Login user and return access token.

    Args:
        login_req: Login credentials
        db: Database connection

    Returns:
        Access token

    Raises:
        HTTPException: If credentials are invalid (401)
    """
    service = AuthService(db)

    try:
        token = await service.login(
            email=login_req.email,
            password=login_req.password,
        )
        return TokenResponse(access_token=token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """
    Dependency to get current user ID from JWT token.

    Args:
        credentials: HTTP bearer credentials

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid (401)
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        token = credentials.credentials
        user_id = verify_access_token(token)
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


@router.get("/me", response_model=User)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Get current authenticated user.

    Args:
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Current user object

    Raises:
        HTTPException: If user not found (404)
    """
    service = AuthService(db)

    try:
        user = await service.get_user_by_id(user_id)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
