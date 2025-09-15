# app/api/v1/users.py

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import User, UserDetail
from app.services.user_service import UserService
from app.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user

router = APIRouter()

@router.get("/{user_id}", response_model=UserDetail)
async def get_user_detail(
    user_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """사용자 상세 정보 조회"""
    user_service = UserService()

    try:
        user_detail = await user_service.get_user_detail(user_id, current_user)

        if not user_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )

        return user_detail

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/me", response_model=UserDetail)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 프로필 조회"""
    user_service = UserService()

    try:
        user_detail = await user_service.get_user_detail(current_user.user_id, current_user)
        return user_detail

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/dev/all", response_model=list[User])
async def get_all_users(db: Session = Depends(get_db)):
    """DB 전체 사용자 조회"""
    user_service = UserService()
    
    try:
        users = await user_service.get_all_users()
        return users
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
