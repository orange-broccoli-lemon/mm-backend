from typing import List
from fastapi import APIRouter, HTTPException, Query, Path
from app.schemas import Movie
from app.services.tmdb_service import TMDBService

router = APIRouter()
tmdb_service = TMDBService()

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
