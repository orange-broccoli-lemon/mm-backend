# app/api/v1/movies.py

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from app.schemas import Movie
from app.services.tmdb_service import TMDBService
from app.services.movie_service import MovieService
from app.schemas.movie import (
    Movie,
    MovieLike,
    MovieLikeRequest,
    Watchlist,
    WatchlistRequest,
    WatchlistMovie,
    MovieWithUserActions,
)
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models import UserModel as User
from app.services.comment_service import CommentService
from app.schemas.comment import Comment, CommentCreate

router = APIRouter()
tmdb_service = TMDBService()


def get_movie_service() -> MovieService:
    return MovieService()


def get_comment_service() -> CommentService:
    return CommentService()


@router.get(
    "/popular",
    response_model=List[Movie],
    summary="인기 영화 10개",
    description="TMDB에서 한국 기준 인기 영화 10개를 조회합니다.",
)
async def get_popular_movies(
    language: str = Query(
        default="ko-KR",
        description="언어 코드 (ko-KR: 한국어, en-US: 영어)",
        regex="^[a-z]{2}-[A-Z]{2}$",
    )
):
    """인기 영화 10개 조회"""
    try:
        movies = await tmdb_service.get_popular_movies_top10(language=language)
        return movies
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"인기 영화를 불러오는데 실패했습니다: {str(e)}"
        )


@router.get(
    "/{movie_id}",
    response_model=Dict[str, Any],
    summary="영화 상세 정보",
    description="영화 상세 정보를 조회합니다. DB → TMDB 순으로 조회합니다.",
)
async def get_movie_details(
    movie_id: int = Path(description="TMDB 영화 ID"),
    language: str = Query(default="ko-KR", description="언어 코드", regex="^[a-z]{2}-[A-Z]{2}$"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    movie_service: MovieService = Depends(get_movie_service),
):
    try:
        user_id = current_user.user_id if current_user else None
        movie_with_actions = await movie_service.get_movie_detail(movie_id, user_id)
        if movie_with_actions:
            return movie_with_actions
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"영화를 찾을 수 없습니다 (ID: {movie_id})",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"영화 상세 정보를 불러오는데 실패했습니다: {str(e)}",
        )


@router.get(
    "/{movie_id}/genres",
    summary="영화 장르 조회",
    description="특정 영화의 장르 목록을 조회합니다.",
)
async def get_movie_genres(
    movie_id: int = Path(description="영화 ID"),
    movie_service: MovieService = Depends(get_movie_service),
):
    try:
        genres = await movie_service.get_movie_genres(movie_id)
        return {"movie_id": movie_id, "genres": genres}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{movie_id}/cast",
    summary="영화 출연진 조회",
    description="특정 영화의 출연진 정보를 조회합니다.",
)
async def get_movie_cast_only(
    movie_id: int = Path(description="영화 ID"),
    movie_service: MovieService = Depends(get_movie_service),
):
    try:
        movie_with_cast = await movie_service.get_movie_by_movie_id(movie_id)

        if not movie_with_cast:
            raise HTTPException(status_code=404, detail="영화를 찾을 수 없습니다")

        return {
            "movie_id": movie_id,
            "cast": movie_with_cast.get("cast", []),
            "crew": movie_with_cast.get("crew", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{movie_id}/like",
    response_model=MovieLike,
    summary="영화 좋아요",
    description="특정 영화에 좋아요를 추가합니다. 이미 좋아요한 영화인 경우 에러를 반환합니다.",
)
async def like_movie(
    movie_id: int = Path(description="좋아요할 영화 ID"),
    current_user: User = Depends(get_current_user),
    movie_service: MovieService = Depends(get_movie_service),
):
    """영화 좋아요"""
    try:
        like = await movie_service.like_movie(current_user.user_id, movie_id)
        return like

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{movie_id}/like",
    summary="영화 좋아요 취소",
    description="특정 영화의 좋아요를 취소합니다. 좋아요하지 않은 영화인 경우 에러를 반환합니다.",
)
async def unlike_movie(
    movie_id: int = Path(description="좋아요 취소할 영화 ID"),
    current_user: User = Depends(get_current_user),
    movie_service: MovieService = Depends(get_movie_service),
):
    """영화 좋아요 취소"""
    try:
        success = await movie_service.unlike_movie(current_user.user_id, movie_id)
        return {"message": "좋아요가 취소되었습니다", "success": success}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{movie_id}/watchlist",
    response_model=Watchlist,
    summary="왓치리스트에 영화 추가",
    description="특정 영화를 사용자의 왓치리스트에 추가합니다. 이미 왓치리스트에 있는 영화인 경우 에러를 반환합니다.",
)
async def add_to_watchlist(
    movie_id: int = Path(description="왓치리스트에 추가할 영화 ID"),
    current_user: User = Depends(get_current_user),
    movie_service: MovieService = Depends(get_movie_service),
):
    """왓치리스트에 영화 추가"""
    try:
        watchlist = await movie_service.add_to_watchlist(current_user.user_id, movie_id)
        return watchlist

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{movie_id}/watchlist",
    summary="왓치리스트에서 영화 제거",
    description="사용자의 왓치리스트에서 특정 영화를 제거합니다. 왓치리스트에 없는 영화인 경우 에러를 반환합니다.",
)
async def remove_from_watchlist(
    movie_id: int = Path(description="왓치리스트에서 제거할 영화 ID"),
    current_user: User = Depends(get_current_user),
    movie_service: MovieService = Depends(get_movie_service),
):
    """왓치리스트에서 영화 제거"""
    try:
        success = await movie_service.remove_from_watchlist(current_user.user_id, movie_id)
        return {"message": "왓치리스트에서 제거되었습니다", "success": success}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{movie_id}/comments",
    response_model=List[Comment],
    summary="영화 댓글 목록",
    description="특정 영화의 댓글을 조회합니다.",
)
async def list_movie_comments(
    movie_id: int = Path(description="영화 ID"),
    include_spoilers: bool = Query(default=False, description="스포일러 포함 여부"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Optional[User] = Depends(get_optional_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    try:
        current_user_id = current_user.user_id if current_user else None
        return await comment_service.get_movie_comments(
            movie_id, current_user_id, include_spoilers, limit, offset
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{movie_id}/comments",
    response_model=Comment,
    summary="영화 댓글 작성",
    description="특정 영화에 댓글을 작성합니다.",
)
async def create_movie_comment(
    movie_id: int = Path(description="영화 ID"),
    comment_data: CommentCreate = ...,
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    try:
        comment_data.movie_id = movie_id
        return await comment_service.create_comment(comment_data, current_user.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/",
    response_model=List[Movie],
    summary="DB 영화 목록",
    description="데이터베이스에 저장된 모든 영화 목록을 조회합니다.",
)
async def get_all_movies(
    skip: int = Query(default=0, ge=0, description="건너뛸 영화 수"),
    limit: int = Query(default=50, ge=1, le=100, description="가져올 영화 수"),
    movie_service: MovieService = Depends(get_movie_service),
):
    try:
        movies = await movie_service.get_all_movies(skip, limit)
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
