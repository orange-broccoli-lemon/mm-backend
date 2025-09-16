# app/api/v1/users.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from app.schemas.user import User, UserDetail
from app.services.user_service import UserService
from app.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.schemas.movie import WatchlistMovie
from app.services.movie_service import MovieService
from app.services.comment_service import CommentService
from app.schemas.comment import CommentWithMovie

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
    "/{user_id}/watchlist",
    response_model=List[WatchlistMovie],
    summary="사용자 왓치리스트 조회",
    description="특정 사용자의 왓치리스트에 추가된 영화 목록을 조회합니다."
)
async def get_user_watchlist(
    user_id: int = Path(description="조회할 사용자 ID"),
    limit: int = Query(default=20, ge=1, le=100, description="가져올 영화 수"),
    offset: int = Query(default=0, ge=0, description="건너뛸 영화 수"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """사용자 왓치리스트 조회"""
    movie_service = MovieService()
    
    try:
        # 사용자 존재 확인
        user_service = UserService()
        target_user = await user_service.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        watchlist = await movie_service.get_user_watchlist(user_id, limit, offset)
        return watchlist
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/{user_id}/liked-movies",
    response_model=List[WatchlistMovie],
    summary="사용자가 좋아요한 영화",
    description="특정 사용자가 좋아요한 영화 목록을 조회합니다."
)
async def get_user_liked_movies(
    user_id: int = Path(description="조회할 사용자 ID"),
    limit: int = Query(default=20, ge=1, le=100, description="가져올 영화 수"),
    offset: int = Query(default=0, ge=0, description="건너뛸 영화 수"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """사용자가 좋아요한 영화 목록"""
    movie_service = MovieService()
    
    try:
        # 사용자 존재 확인
        user_service = UserService()
        target_user = await user_service.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        liked_movies = await movie_service.get_user_liked_movies(user_id, limit, offset)
        return liked_movies
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/{user_id}/comments",
    response_model=List[CommentWithMovie],
    summary="사용자 댓글 목록",
    description="특정 사용자가 작성한 댓글 목록을 조회합니다. 본인이 아닌 경우 공개 댓글만 조회됩니다."
)
async def get_user_comments(
    user_id: int = Path(description="조회할 사용자 ID"),
    limit: int = Query(default=20, ge=1, le=100, description="가져올 댓글 수"),
    offset: int = Query(default=0, ge=0, description="건너뛸 댓글 수"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """사용자 댓글 목록 조회"""
    comment_service = CommentService()
    
    try:
        # 사용자 존재 확인
        user_service = UserService()
        target_user = await user_service.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 본인 여부 확인
        is_own_profile = current_user and current_user.user_id == user_id
        
        comments = await user_service.get_user_comments_with_movies(
            user_id, limit, offset, is_own_profile
        )
        return comments
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/dev/all", 
    response_model=List[User],
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