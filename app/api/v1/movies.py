# app/api/v1/movies.py

from typing import List
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from app.schemas import Movie
from app.services.tmdb_service import TMDBService
from app.services.movie_service import MovieService

router = APIRouter()
tmdb_service = TMDBService()

def get_movie_service() -> MovieService:
    return MovieService()

@router.get(
    "/popular",
    response_model=List[Movie],
    summary="인기 영화 10개",
    description="TMDB에서 한국 기준 인기 영화 10개를 조회합니다."
)
async def get_popular_movies(
    language: str = Query(
        default="ko-KR",
        description="언어 코드 (ko-KR: 한국어, en-US: 영어)",
        regex="^[a-z]{2}-[A-Z]{2}$"
    )
):
    """인기 영화 10개 조회"""
    try:
        movies = await tmdb_service.get_popular_movies_top10(language=language)
        return movies
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"인기 영화를 불러오는데 실패했습니다: {str(e)}"
        )

@router.get(
    "/{movie_id}",
    response_model=Movie,
    summary="영화 상세 정보",
    description="영화 상세 정보를 조회합니다. DB에서 먼저 찾고, 없으면 TMDB API에서 가져와 저장합니다."
)
async def get_movie_details(
    movie_id: int = Path(description="TMDB 영화 ID"),
    language: str = Query(
        default="ko-KR",
        description="언어 코드",
        regex="^[a-z]{2}-[A-Z]{2}$"
    ),
    movie_service: MovieService = Depends(get_movie_service)
):
    """영화 상세 정보 조회"""
    try:
        movie = await movie_service.get_movie_by_movie_id(movie_id)
        
        if movie:
            return movie
        
        tmdb_raw_data = await tmdb_service.get_movie_details(movie_id=movie_id, language=language)
        saved_movie = await movie_service.save_movie_from_tmdb_data(tmdb_raw_data)
        
        return saved_movie
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"영화 상세 정보를 불러오는데 실패했습니다: {str(e)}"
        )

@router.get(
    "/",
    response_model=List[Movie],
    summary="DB 영화 목록",
    description="데이터베이스에 저장된 모든 영화 목록을 조회합니다."
)
async def get_all_movies(
    skip: int = Query(default=0, ge=0, description="건너뛸 영화 수"),
    limit: int = Query(default=50, ge=1, le=100, description="가져올 영화 수"),
    movie_service: MovieService = Depends(get_movie_service)
):
    try:
        movies = await movie_service.get_all_movies(skip, limit)
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))