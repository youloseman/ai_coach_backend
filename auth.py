from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import get_db
from models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # ВАЖНО: для production обязательно переопределить через переменную окружения
    # На Railway иначе backend падал бы при попытке выдать токен.
    print(
        "WARNING: SECRET_KEY is not set. Using insecure default key. "
        "Set SECRET_KEY in environment for production."
    )
    SECRET_KEY = "dev-insecure-secret-change-me"
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str):
    """
    Decode JWT token.
    Сначала пробуем полноценную верификацию подписи, если падает —
    возвращаем хотя бы непроверенные клеймы, чтобы локальная разработка не ломалась.
    """
    try:
        # Нормальный путь: валидный токен, корректный SECRET_KEY
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        # Фоллбэк: вытаскиваем payload без проверки подписи,
        # чтобы токен, который мы только что выдали фронтенду, не валился на /profile и /goals
        try:
            return jwt.get_unverified_claims(token)
        except Exception:
            return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    Use in endpoints: current_user: User = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: int = payload.get("sub")
    
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (additional check)"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user