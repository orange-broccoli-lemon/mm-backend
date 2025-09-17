# app/api/v1/search.py

import re
from fastapi import APIRouter, HTTPException, Query
from app.schemas import SearchResponse
from app.services.tmdb_service import TMDBService

router = APIRouter()
tmdb_service = TMDBService()


def filter_korean_incomplete_chars(text: str) -> str:
    """한국어 미완성 문자를 필터링하고 완성된 문자만 남김"""

    filtered_text = ""
    for char in text:
        if not 0x3131 <= ord(char) <= 0x3163:
            filtered_text += char

    # 연속된 공백을 하나로 정리하고 앞뒤 공백 제거
    filtered_text = re.sub(r"\s+", " ", filtered_text).strip()

    return filtered_text


def is_valid_search_query(query: str) -> bool:
    """검색어가 유효한지 확인"""
    return query and len(query.strip()) > 0


@router.get(
    "", response_model=SearchResponse, summary="검색", description="영화와 인물을 검색합니다."
)
async def search_all(
    query: str = Query(description="검색할 키워드", min_length=1),
    language: str = Query(
        default="ko-KR",
        description="언어 코드 (ko-KR: 한국어, en-US: 영어)",
        regex="^[a-z]{2}-[A-Z]{2}$",
    ),
):
    """검색"""
    try:
        filtered_query = filter_korean_incomplete_chars(query)

        print(f"필터링된 검색어: '{filtered_query}'")

        # 필터링 후 유효한 검색어인지 확인
        if not is_valid_search_query(filtered_query):
            raise HTTPException(
                status_code=400,
                detail="검색할 수 있는 완성된 문자가 없습니다. 완성된 한글이나 영문을 입력해주세요.",
            )

        search_results = await tmdb_service.multi_search(query=filtered_query, language=language)
        return SearchResponse(results=search_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색에 실패했습니다: {str(e)}")
