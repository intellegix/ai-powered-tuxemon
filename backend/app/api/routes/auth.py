# Authentication API Routes for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.game.models import Player

settings = get_settings()
security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


# Pydantic models
class PlayerRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class PlayerLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class PlayerProfile(BaseModel):
    id: UUID
    username: str
    email: str
    current_map: str
    money: int
    play_time_seconds: int
    created_at: datetime
    last_login: Optional[datetime]


# Authentication utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


async def get_current_player(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Player:
    """Get current authenticated player."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        player_id: str = payload.get("sub")
        if player_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Get player from database
    from sqlmodel import select
    result = await db.execute(select(Player).where(Player.id == UUID(player_id)))
    player = result.scalar_one_or_none()

    if player is None or not player.is_active:
        raise credentials_exception

    # Update last login
    player.last_login = datetime.utcnow()
    db.add(player)
    await db.commit()

    return player


# API Routes
@router.post("/register", response_model=Token)
async def register_player(player_data: PlayerRegister, db: AsyncSession = Depends(get_db)):
    """Register a new player account."""
    from sqlmodel import select

    # Check if username already exists
    result = await db.execute(select(Player).where(Player.username == player_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    result = await db.execute(select(Player).where(Player.email == player_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new player
    hashed_password = get_password_hash(player_data.password)
    new_player = Player(
        username=player_data.username,
        email=player_data.email,
        hashed_password=hashed_password,
        current_map="starting_town",
        position_x=5,
        position_y=5,
        money=500,  # Starting money
        story_progress="{}",
        npc_relationships="{}",
    )

    db.add(new_player)
    await db.commit()
    await db.refresh(new_player)

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(new_player.id)},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/login", response_model=Token)
async def login_player(player_data: PlayerLogin, db: AsyncSession = Depends(get_db)):
    """Login with username and password."""
    from sqlmodel import select

    # Find player by username
    result = await db.execute(select(Player).where(Player.username == player_data.username))
    player = result.scalar_one_or_none()

    if not player or not verify_password(player_data.password, player.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not player.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is disabled"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(player.id)},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.get("/profile", response_model=PlayerProfile)
async def get_player_profile(current_player: Player = Depends(get_current_player)):
    """Get current player's profile."""
    return PlayerProfile(
        id=current_player.id,
        username=current_player.username,
        email=current_player.email,
        current_map=current_player.current_map,
        money=current_player.money,
        play_time_seconds=current_player.play_time_seconds,
        created_at=current_player.created_at,
        last_login=current_player.last_login,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(current_player: Player = Depends(get_current_player)):
    """Refresh access token."""
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(current_player.id)},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout_player(current_player: Player = Depends(get_current_player)):
    """Logout player (token invalidation handled client-side)."""
    return {"message": "Successfully logged out"}