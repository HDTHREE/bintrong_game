from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from pydantic import BaseModel
from datetime import datetime
import uuid

from livetrivia.db import SqlSession
from livetrivia.models.round import Round
from livetrivia.models.game import Game
from livetrivia.models.session import Session
from livetrivia.models.status import Status
from livetrivia.jwt_utils import verify_token
from livetrivia.routes.session import BearerCredentials

router: APIRouter = APIRouter(prefix="/rounds", tags=["rounds"])


class RoundResponse(BaseModel):
    id: uuid.UUID
    game_id: uuid.UUID
    status: Status
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None

    class Config:
        from_attributes = True


@router.post(
    "/{game_id}", response_model=RoundResponse, status_code=status.HTTP_201_CREATED
)
async def create_round(
    game_id: uuid.UUID,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> Round:
    access_token = credentials.credentials
    user_id = verify_token(access_token, token_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token) & (Session.is_active)
    )
    result = await sql.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive",
        )

    stmt = select(Game).where(Game.id == game_id)
    result = await sql.execute(stmt)
    game = result.scalars().first()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    if game.host_session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can create rounds",
        )

    if game.status != Status.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rounds can only be created for games in RUNNING status",
        )

    new_round = Round(game_id=game.id)
    sql.add(new_round)
    await sql.commit()
    await sql.refresh(new_round)

    return new_round


@router.post(
    "/{round_id}/start", response_model=RoundResponse, status_code=status.HTTP_200_OK
)
async def start_round(
    round_id: uuid.UUID,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> Round:
    access_token = credentials.credentials
    user_id = verify_token(access_token, token_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token) & (Session.is_active)
    )
    result = await sql.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive",
        )

    stmt = select(Round).where(Round.id == round_id)
    result = await sql.execute(stmt)
    round_obj = result.scalars().first()

    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    stmt = select(Game).where(Game.id == round_obj.game_id)
    result = await sql.execute(stmt)
    game = result.scalars().first()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    if game.host_session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can start rounds",
        )

    if round_obj.status != Status.STARTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round must be in STARTING status to start",
        )

    round_obj.status = Status.RUNNING
    round_obj.started_at = datetime.now()
    sql.add(round_obj)
    await sql.commit()
    await sql.refresh(round_obj)

    return round_obj


@router.post(
    "/{round_id}/end", response_model=RoundResponse, status_code=status.HTTP_200_OK
)
async def end_round(
    round_id: uuid.UUID,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> Round:
    access_token = credentials.credentials
    user_id = verify_token(access_token, token_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    stmt = select(Session).where(
        (Session.access_token == access_token) & (Session.is_active)
    )
    result = await sql.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or inactive",
        )

    stmt = select(Round).where(Round.id == round_id)
    result = await sql.execute(stmt)
    round_obj = result.scalars().first()

    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round not found"
        )

    stmt = select(Game).where(Game.id == round_obj.game_id)
    result = await sql.execute(stmt)
    game = result.scalars().first()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    if game.host_session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can end rounds",
        )

    if round_obj.status != Status.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round must be in RUNNING status to end",
        )

    round_obj.status = Status.ENDED
    round_obj.ended_at = datetime.now()
    sql.add(round_obj)
    await sql.commit()
    await sql.refresh(round_obj)

    return round_obj
