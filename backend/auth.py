"""Authentication module with bcrypt hashing and JWT tokens."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from backend.database import get_db, User, LoginAttempt
import os

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate bcrypt hash of password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def check_login_attempts(db: Session, username: str, ip_address: str) -> bool:
    """Check if user is locked out due to failed attempts."""
    lockout_time = datetime.utcnow() - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    
    # Count failed attempts in lockout window
    failed_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.username == username,
        LoginAttempt.success == False,
        LoginAttempt.attempted_at > lockout_time
    ).count()
    
    return failed_attempts >= MAX_LOGIN_ATTEMPTS

def record_login_attempt(db: Session, username: str, ip_address: str, success: bool):
    """Record login attempt for audit."""
    attempt = LoginAttempt(
        username=username,
        ip_address=ip_address,
        success=success
    )
    db.add(attempt)
    db.commit()

def authenticate_user(db: Session, username: str, password: str, ip_address: str = None):
    """Authenticate user with username and password."""
    # Check for lockout
    if check_login_attempts(db, username, ip_address):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Hesap kilitlendi. {LOCKOUT_DURATION_MINUTES} dakika sonra tekrar deneyin."
        )
    
    # Get user
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        record_login_attempt(db, username, ip_address, False)
        return None
    
    if not user.is_active:
        record_login_attempt(db, username, ip_address, False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesap devre dışı bırakılmış."
        )
    
    if not verify_password(password, user.password_hash):
        record_login_attempt(db, username, ip_address, False)
        return None
    
    # Success - update last login and record
    user.last_login = datetime.utcnow()
    record_login_attempt(db, username, ip_address, True)
    db.commit()
    
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesap devre dışı bırakılmış."
        )
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Verify user is active."""
    return current_user

async def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin yetkisi gerekli."
        )
    return current_user

def create_user(db: Session, username: str, email: str, password: str, 
                full_name: str, role: str = "doctor", department: str = "Genel"):
    """Create new user with hashed password."""
    # Check if user exists
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kullanıcı adı zaten kullanılıyor."
        )
    
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email adresi zaten kullanılıyor."
        )
    
    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        role=role,
        department=department
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
