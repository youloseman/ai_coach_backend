"""
strava_auth.py - Multi-user Strava authentication
"""

from sqlalchemy.orm import Session
from models import User
from config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, logger
import httpx
import datetime as dt
from typing import Optional


async def get_user_tokens(user_id: int, db: Session) -> dict:
    """
    Получить актуальные Strava токены для пользователя.
    Автоматически обновляет если истекли.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    if not user.strava_access_token:
        raise ValueError(f"User {user_id} not connected to Strava")
    
    # Проверить валидность токена
    now = dt.datetime.now()
    if user.strava_token_expires_at and user.strava_token_expires_at <= now:
        # Токен истек - обновить
        logger.info("refreshing_strava_token", user_id=user_id)
        new_tokens = await refresh_token(user.strava_refresh_token)
        
        user.strava_access_token = new_tokens["access_token"]
        user.strava_refresh_token = new_tokens["refresh_token"]
        user.strava_token_expires_at = dt.datetime.fromtimestamp(new_tokens["expires_at"])
        db.commit()
        db.refresh(user)
    
    return {
        "access_token": user.strava_access_token,
        "refresh_token": user.strava_refresh_token,
        "expires_at": user.strava_token_expires_at,
        "athlete_id": user.strava_athlete_id,
    }


async def refresh_token(refresh_token: str) -> dict:
    """Обновить Strava токен"""
    url = "https://www.strava.com/api/v3/oauth/token"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
        response.raise_for_status()
        return response.json()


async def save_strava_tokens(
    user_id: int,
    athlete_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: int,
    db: Session
) -> User:
    """Сохранить Strava токены для пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    user.strava_athlete_id = athlete_id
    user.strava_access_token = access_token
    user.strava_refresh_token = refresh_token
    user.strava_token_expires_at = dt.datetime.fromtimestamp(expires_at)
    
    db.commit()
    db.refresh(user)
    
    logger.info("strava_tokens_saved", user_id=user_id, athlete_id=athlete_id)
    return user


async def save_user_tokens(user_id: int, db: Session, token_data: dict) -> User:
    """
    Сохранить Strava токены для пользователя из словаря token_data.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    user.strava_access_token = token_data.get("access_token")
    user.strava_refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")
    if expires_at:
        user.strava_token_expires_at = dt.datetime.fromtimestamp(expires_at)
    if token_data.get("athlete", {}).get("id"):
        user.strava_athlete_id = str(token_data["athlete"]["id"])
    
    db.commit()
    db.refresh(user)
    logger.info("strava_tokens_saved_from_dict", user_id=user_id)
    return user


async def disconnect_strava(user_id: int, db: Session) -> None:
    """Отключить Strava для пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    user.strava_athlete_id = None
    user.strava_access_token = None
    user.strava_refresh_token = None
    user.strava_token_expires_at = None
    
    db.commit()
    logger.info("strava_disconnected", user_id=user_id)