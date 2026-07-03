import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> Token:
    """Register a new user account and return a JWT token.

    - Email and username must be unique.
    - Password is bcrypt-hashed before storage.
    """
    # Check email uniqueness
    existing_email = await db.execute(select(User).where(User.email == payload.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Check username uniqueness
    existing_username = await db.execute(
        select(User).where(User.username == payload.username)
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    # Create the user
    new_user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(new_user)
    await db.flush()   # get the id without committing yet
    await db.refresh(new_user)

    # Issue JWT
    role_str = new_user.role.value if hasattr(new_user.role, "value") else new_user.role
    token = create_access_token({"sub": new_user.id, "role": role_str})
    return Token(access_token=token, user=UserOut.model_validate(new_user))


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate with email + password and return a JWT token."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    role_str = user.role.value if hasattr(user.role, "value") else user.role
    token = create_access_token({"sub": user.id, "role": role_str})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the currently authenticated user's profile."""
    return UserOut.model_validate(current_user)
