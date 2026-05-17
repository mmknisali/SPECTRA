"""Authentication and user management routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta

from backend.database import get_db, User
from backend.auth import (
    authenticate_user, create_access_token, create_user, get_current_user,
    require_admin, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Pydantic schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: str = "doctor"
    department: str = "Genel"
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "dr.ayse",
                "email": "ayse@hospital.gov.tr",
                "password": "SecurePass123!",
                "full_name": "Dr. Ayşe Yılmaz",
                "role": "doctor",
                "department": "Onkoloji"
            }
        }

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    department: str
    is_active: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[Token] = None

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    # Get client IP
    ip_address = request.client.host
    
    # Authenticate
    user = authenticate_user(db, form_data.username, form_data.password, ip_address)
    
    if not user:
        return LoginResponse(
            success=False,
            message="Geçersiz kullanıcı adı veya şifre."
        )
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        success=True,
        message="Giriş başarılı.",
        token=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
    )

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Register new user (admin only)."""
    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=user_data.role,
        department=user_data.department
    )
    return UserResponse.model_validate(user)

@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout current user (token invalidation handled client-side)."""
    return {"success": True, "message": "Çıkış başarılı."}

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(u) for u in users]

@router.put("/users/{user_id}/toggle", response_model=UserResponse)
async def toggle_user_status(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Enable/disable user account (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kendi hesabınızı devre dışı bırakamazsınız."
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
