# app/core/dependencies.py

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.user import User
from app.services.user_service import UserService
from app.core.auth import verify_token

security = HTTPBearer(auto_error=False)

def get_user_service() -> UserService:
    return UserService()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_service: UserService = Depends(get_user_service)
) -> User:
    """현재 로그인한 사용자 조회"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 필요합니다"
        )
    
    token = credentials.credentials
    email = verify_token(token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다"
        )
    
    user = await user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다"
        )
    
    return user

async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_service: UserService = Depends(get_user_service)
) -> Optional[User]:
    """현재 로그인한 사용자 조회 None 허용"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        email = verify_token(token)
        
        if not email:
            return None
        
        user = await user_service.get_user_by_email(email)
        return user
    except Exception:
        return None
