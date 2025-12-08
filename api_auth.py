from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
import models
from schemas import UserCreate, Token, UserResponse
from auth import (
    verify_password, 
    create_access_token, 
    get_current_user,
    create_email_verification_token,
    verify_email_token
)
import crud
from config import logger, FRONTEND_BASE_URL
from email_client import send_html_email


router = APIRouter()


@router.post("/auth/register", response_model=Token)
async def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
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

        # Send verification email
        try:
            verification_token = create_email_verification_token(db_user.id, db_user.email)
            verification_url = f"{FRONTEND_BASE_URL}/verify-email?token={verification_token}"
            
            email_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Welcome to AI Triathlon Coach!</h2>
                    <p>Please verify your email address by clicking the link below:</p>
                    <p><a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
                    <p>Or copy this link to your browser:</p>
                    <p style="word-break: break-all;">{verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                </body>
            </html>
            """
            
            send_html_email(
                to_email=db_user.email,
                subject="Verify your email address",
                html_body=email_html
            )
            logger.info("verification_email_sent", user_id=db_user.id, email=db_user.email)
        except Exception as e:
            # Don't fail registration if email sending fails
            logger.warning("verification_email_failed", user_id=db_user.id, error=str(e))

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
    request: Request,
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


@router.post("/auth/verify-email")
async def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    """Verify user email with verification token"""
    payload = verify_email_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload"
        )
    
    try:
        user = crud.verify_user_email(db, user_id)
        logger.info("email_verified", user_id=user_id)
        return {
            "status": "success",
            "message": "Email verified successfully",
            "user": UserResponse.model_validate(user)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/auth/resend-verification")
async def resend_verification_email(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend verification email to current user"""
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    try:
        verification_token = create_email_verification_token(current_user.id, current_user.email)
        verification_url = f"{FRONTEND_BASE_URL}/verify-email?token={verification_token}"
        
        email_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Verify your email address</h2>
                <p>Please verify your email address by clicking the link below:</p>
                <p><a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
                <p>Or copy this link to your browser:</p>
                <p style="word-break: break-all;">{verification_url}</p>
                <p>This link will expire in 24 hours.</p>
            </body>
        </html>
        """
        
        send_html_email(
            to_email=current_user.email,
            subject="Verify your email address",
            html_body=email_html
        )
        logger.info("verification_email_resent", user_id=current_user.id)
        
        return {
            "status": "success",
            "message": "Verification email sent"
        }
    except Exception as e:
        logger.error("resend_verification_failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


