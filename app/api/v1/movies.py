# app/api/v1/movies.py

from typing import List, Dict, Any
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
    response_model=Dict[str, Any],  # Movie → Dict[str, Any]로 변경
    summary="영화 상세 정보 (출연진 포함)",
    description="영화 상세 정보와 출연진을 함께 조회합니다. DB에서 먼저 찾고, 없으면 TMDB API에서 가져와 저장합니다."
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
    """영화 상세 정보 조회 (출연진 포함)"""
    try:
        # MovieService의 get_movie_by_movie_id는 이미 출연진 포함 dict 반환
        movie_with_cast = await movie_service.get_movie_by_movie_id(movie_id)
        
        if movie_with_cast:
            return movie_with_cast  # 출연진 포함된 dict 반환
        
        # 영화를 찾을 수 없는 경우
        raise HTTPException(
            status_code=404,
            detail=f"영화를 찾을 수 없습니다 (ID: {movie_id})"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"영화 상세 정보를 불러오는데 실패했습니다: {str(e)}"
        )

@router.get(
    "/{movie_id}/basic",
    response_model=Movie,
    summary="영화 기본 정보만",
    description="영화 기본 정보만 조회합니다 (출연진 제외)."
)
async def get_movie_basic_info(
    movie_id: int = Path(description="TMDB 영화 ID"),
    movie_service: MovieService = Depends(get_movie_service)
):
    """영화 기본 정보만 조회"""
    try:
        movie_with_cast = await movie_service.get_movie_by_movie_id(movie_id)
        
        if not movie_with_cast:
            raise HTTPException(status_code=404, detail="영화를 찾을 수 없습니다")
        
        # cast, crew 제외하고 기본 정보만 반환
        movie_basic = {k: v for k, v in movie_with_cast.items() if k not in ['cast', 'crew']}
        return movie_basic
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get(
    "/{movie_id}/genres",
    summary="영화 장르 조회",
    description="특정 영화의 장르 목록을 조회합니다."
)
async def get_movie_genres(
    movie_id: int = Path(description="영화 ID"),
    movie_service: MovieService = Depends(get_movie_service)
):
    try:
        genres = await movie_service.get_movie_genres(movie_id)
        return {"movie_id": movie_id, "genres": genres}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{movie_id}/cast",
    summary="영화 출연진만 조회",
    description="특정 영화의 출연진 정보만 조회합니다."
)
async def get_movie_cast_only(
    movie_id: int = Path(description="영화 ID"),
    movie_service: MovieService = Depends(get_movie_service)
):
    try:
        movie_with_cast = await movie_service.get_movie_by_movie_id(movie_id)
        
        if not movie_with_cast:
            raise HTTPException(status_code=404, detail="영화를 찾을 수 없습니다")
        
        return {
            "movie_id": movie_id,
            "cast": movie_with_cast.get("cast", []),
            "crew": movie_with_cast.get("crew", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
