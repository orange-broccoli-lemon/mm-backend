import re
from typing import List
from fastapi import APIRouter, HTTPException, Query
from app.schemas.search import (
    SearchResponse,
    MovieSearchResult,
    PersonSearchResult,
    UserSearchResult,
)
from app.services.tmdb_service import TMDBService
from app.services.user_service import UserService

router = APIRouter()
tmdb_service = TMDBService()
user_service = UserService()


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
    "",
    response_model=SearchResponse,
    summary="통합 검색",
    description="영화, 인물, 사용자를 검색하여 분류별로 반환합니다.",
)
async def search_all(
    query: str = Query(description="검색할 키워드", min_length=1),
    language: str = Query(
        default="ko-KR",
        description="언어 코드 (ko-KR: 한국어, en-US: 영어)",
        regex="^[a-z]{2}-[A-Z]{2}$",
    ),
):
    """통합 검색"""
    try:
        filtered_query = filter_korean_incomplete_chars(query)
        print(f"필터링된 검색어: '{filtered_query}'")

        # 필터링 후 유효한 검색어인지 확인
        if not is_valid_search_query(filtered_query):
            raise HTTPException(
                status_code=400,
                detail="검색할 수 있는 완성된 문자가 없습니다. 완성된 한글이나 영문을 입력해주세요.",
            )

        # TMDB 검색
        tmdb_results = await tmdb_service.multi_search(query=filtered_query, language=language)

        # 사용자 검색
        user_results = await user_service.search_users_by_name(name=filtered_query)

        # 결과 분류
        movies = []
        persons = []

        for result in tmdb_results:
            if isinstance(result, MovieSearchResult):
                movies.append(result)
            elif isinstance(result, PersonSearchResult):
                persons.append(result)

        # 최대 10개씩 제한
        movies = movies[:10]
        persons = persons[:10]
        users = user_results[:10]

        return SearchResponse(
            movies=movies,
            persons=persons,
            users=users,
            movie_count=len(movies),
            person_count=len(persons),
            user_count=len(users),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"검색 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검색에 실패했습니다: {str(e)}")
