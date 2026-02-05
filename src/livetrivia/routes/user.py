from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from pydantic import BaseModel, EmailStr
import bcrypt
import uuid

from livetrivia.models.user import User, LoginRequest
from livetrivia.db import SqlSession

router: APIRouter = APIRouter(prefix="/users", tags=["users"])


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
    user_data: LoginRequest,
    sql: SqlSession,
) -> "User":
    """Create a new user with email and password."""
    stmt = select(User).where(User.email == user_data.email)
    result = await sql.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = hash_password(user_data.password)

    new_user = User(email=user_data.email, password=hashed_password)
    sql.add(new_user)
    await sql.commit()
    await sql.refresh(new_user)

    return new_user
