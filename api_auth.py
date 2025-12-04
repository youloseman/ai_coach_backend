from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
import models
from schemas import UserCreate, Token, UserResponse
from auth import verify_password, create_access_token, get_current_user
import crud
from config import logger


router = APIRouter()


@router.post("/auth/register", response_model=Token)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and return access token."""
    try:
        # bcrypt (через passlib) поддерживает только первые 72 байта пароля,
        # поэтому слишком длинные пароли приводят к ValueError на сервере.
        # Явно ограничиваем длину и возвращаем понятную ошибку.
        if len(user.password.encode("utf-8")) > 72:
            raise HTTPException(
                status_code=400,
                detail="Password too long. Please use a password up to 72 characters.",
            )

        if crud.get_user_by_email(db, user.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        if crud.get_user_by_username(db, user.username):
            raise HTTPException(status_code=400, detail="Username already taken")

        db_user = crud.create_user(db, user)
        crud.update_user_last_login(db, db_user.id)

        access_token = create_access_token(data={"sub": db_user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(db_user),
        }
    except HTTPException:
        # уже подготовленные понятные ошибки пробрасываем как есть
        raise
    except ValueError as e:
        # Специально перехватываем ошибки passlib/bcrypt про 72 байта,
        # чтобы не возвращать 500 и не палить внутренние детали реализации.
        logger.error("auth_register_password_value_error", error=str(e))
        raise HTTPException(
            status_code=400,
            detail="Password too long. Please use a password up to 72 characters.",
        )
    except Exception as e:
        # логируем неожиданную ошибку и возвращаем человекочитаемое сообщение
        logger.error("auth_register_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during registration: {str(e)}",
        )


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login by email/password and return access token."""
    user = crud.get_user_by_email(db, form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    crud.update_user_last_login(db, user.id)
    access_token = create_access_token(data={"sub": user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: models.User = Depends(get_current_user)):
    """Return current authenticated user."""
    return UserResponse.model_validate(current_user)


