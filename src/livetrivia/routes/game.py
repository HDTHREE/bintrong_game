from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from pydantic import BaseModel
from datetime import datetime
import uuid

from livetrivia.db import SqlSession
from livetrivia.docker_manager import spawn_game_server, stop_game_server
from livetrivia.models.files import File
from livetrivia.models.game import Game, GamePlayer
from livetrivia.models.session import Session
from livetrivia.models.status import Status
from livetrivia.jwt_utils import verify_token
from livetrivia.routes.session import BearerCredentials

_ANKI_EXTENSIONS: tuple[str, ...] = (".apkg", ".anki")

router: APIRouter = APIRouter(prefix="/games", tags=["games"])


class GameResponse(BaseModel):
    id: uuid.UUID
    host_session_id: uuid.UUID
    game_code: str | None
    selected_file_id: uuid.UUID | None
    status: Status
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None

    class Config:
        from_attributes = True


class GamePlayerResponse(BaseModel):
    id: uuid.UUID
    game_id: uuid.UUID
    session_id: uuid.UUID
    score: int
    joined_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    sql: SqlSession,
    credentials: BearerCredentials,
) -> Game:
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

    new_game = Game(host_session_id=session.id)
    sql.add(new_game)
    await sql.commit()
    await sql.refresh(new_game)

    return new_game


@router.post(
    "/join", response_model=GamePlayerResponse, status_code=status.HTTP_201_CREATED
)
async def join_game(
    game_code: str,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> GamePlayer:
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

    stmt = select(Game).where(Game.game_code == game_code)
    result = await sql.execute(stmt)
    game = result.scalars().first()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    if game.status != Status.STARTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Game not joinable"
        )

    stmt = select(GamePlayer).where(
        (GamePlayer.game_id == game.id) & (GamePlayer.session_id == session.id)
    )
    result = await sql.execute(stmt)
    existing = result.scalars().first()

    if existing and existing.is_active:
        return existing

    new_player = GamePlayer(game_id=game.id, session_id=session.id)
    sql.add(new_player)
    await sql.commit()
    await sql.refresh(new_player)

    return new_player


@router.post(
    "/{game_id}/start", response_model=GameResponse, status_code=status.HTTP_200_OK
)
async def start_game(
    game_id: uuid.UUID,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> Game:
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
            detail="Only the game host can start the game",
        )

    if game.status != Status.STARTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game must be in STARTING status to start",
        )

    game.status = Status.RUNNING
    game.started_at = datetime.now()
    sql.add(game)
    await sql.commit()
    await sql.refresh(game)

    if game.game_code:
        spawn_game_server(game.game_code)

    return game


@router.post(
    "/{game_id}/end", response_model=GameResponse, status_code=status.HTTP_200_OK
)
async def end_game(
    game_id: uuid.UUID,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> Game:
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
            detail="Only the game host can end the game",
        )

    if game.status != Status.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game must be in RUNNING status to end",
        )

    game.status = Status.ENDED
    game.ended_at = datetime.now()
    sql.add(game)
    await sql.commit()
    await sql.refresh(game)

    if game.game_code:
        stop_game_server(game.game_code)

    return game


@router.post(
    "/{game_id}/{player_id}/win",
    response_model=GamePlayerResponse,
    status_code=status.HTTP_200_OK,
)
async def increment_player_score(
    game_id: uuid.UUID,
    player_id: uuid.UUID,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> GamePlayer:
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
            detail="Only the game host can increment player scores",
        )

    stmt = select(GamePlayer).where(
        (GamePlayer.id == player_id) & (GamePlayer.game_id == game_id)
    )
    result = await sql.execute(stmt)
    player = result.scalars().first()

    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found in this game",
        )

    player.score += 1
    sql.add(player)
    await sql.commit()
    await sql.refresh(player)

    return player


@router.post(
    "/{game_id}/file",
    response_model=GameResponse,
    status_code=status.HTTP_200_OK,
)
async def set_game_file(
    game_id: uuid.UUID,
    file_id: uuid.UUID,
    sql: SqlSession,
    credentials: BearerCredentials,
) -> Game:
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
            detail="Only the game host can set the game file",
        )

    if game.status != Status.STARTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game file can only be set while the game is in STARTING status",
        )

    file = await sql.get(File, file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if not any(file.prefix.endswith(ext) for ext in _ANKI_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected file must be an Anki file (.apkg or .anki)",
        )

    game.selected_file_id = file_id
    sql.add(game)
    await sql.commit()
    await sql.refresh(game)

    return game
