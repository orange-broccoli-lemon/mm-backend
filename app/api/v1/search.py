# app/api/v1/search.py

from fastapi import APIRouter, HTTPException, Query
from app.schemas import SearchResponse
from app.services.tmdb_service import TMDBService

router = APIRouter()
tmdb_service = TMDBService()

@router.get(
    "",
    response_model=SearchResponse,
    summary="통합 검색",
    description="영화와 인물(배우/감독)을 검색합니다."
)
async def search_all(
    query: str = Query(description="검색할 키워드", min_length=1),
    language: str = Query(
        default="ko-KR",
        description="언어 코드 (ko-KR: 한국어, en-US: 영어)",
        regex="^[a-z]{2}-[A-Z]{2}$"
    )
):
    """통합 검색"""
    try:
        results = await tmdb_service.multi_search(query=query, language=language)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검색에 실패했습니다: {str(e)}"
        )
