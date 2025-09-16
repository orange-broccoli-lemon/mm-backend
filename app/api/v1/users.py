# app/api/v1/users.py

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import User, UserDetail
from app.services.user_service import UserService
from app.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.schemas.movie import WatchlistMovie
from app.services.movie_service import MovieService

router = APIRouter()

@router.get(
    "/{user_id}", 
    response_model=UserDetail,
    summary="사용자 상세 정보",
    description="특정 사용자의 상세 정보를 조회합니다. 팔로워, 팔로잉, 최근 댓글 등 상세 데이터가 포함됩니다."
)
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

@router.get(
    "/me", 
    response_model=UserDetail,
    summary="내 프로필 조회",
    description="현재 로그인한 사용자의 프로필 정보를 조회합니다. 이메일 등 개인정보도 포함됩니다."
)
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

@router.get(
    "/dev/all", 
    response_model=list[User],
    summary="전체 사용자 조회",
    description="개발용 엔드포인트입니다. DB에 등록된 모든 사용자 목록을 조회합니다."
)
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

@router.get(
    "/me/watchlist",
    response_model=list[WatchlistMovie],
    summary="내 왓치리스트 조회",
    description="현재 로그인한 사용자의 왓치리스트에 추가된 영화 목록을 조회합니다."
)
async def get_my_watchlist(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 왓치리스트 조회"""
    movie_service = MovieService()
    
    try:
        watchlist = await movie_service.get_user_watchlist(current_user.user_id, limit, offset)
        return watchlist
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/me/liked-movies",
    response_model=list[WatchlistMovie],
    summary="내가 좋아요한 영화",
    description="현재 로그인한 사용자가 좋아요한 영화 목록을 조회합니다."
)
async def get_my_liked_movies(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내가 좋아요한 영화 목록"""
    movie_service = MovieService()
    
    try:
        liked_movies = await movie_service.get_user_liked_movies(current_user.user_id, limit, offset)
        return liked_movies
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )