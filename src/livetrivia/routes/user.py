from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
import sqlalchemy.ext.asyncio as sqlas
from pydantic import BaseModel, EmailStr
import bcrypt
import uuid

from livetrivia.models.user import User
from livetrivia.db import get_async_session

router: APIRouter = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr

    class Config:
        from_attributes = True


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    session: sqlas.AsyncSession = Depends(get_async_session),
) -> "User":
    """Create a new user with email and password."""
    # Check if user already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await session.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    hashed_password = hash_password(user_data.password)

    # Create new user
    new_user = User(email=user_data.email, password=hashed_password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user
