# app/schemas/search.py

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class MovieSearchResult(BaseModel):
    """영화 검색 결과"""

    movie_id: int = Field(description="TMDB 영화 ID")
    title: str = Field(description="영화 제목")
    poster_path: Optional[str] = Field(default=None, description="포스터 경로")


class PersonSearchResult(BaseModel):
    """인물 검색 결과"""

    person_id: int = Field(description="TMDB 인물 ID")
    name: str = Field(description="인물 이름")
    profile_path: Optional[str] = Field(default=None, description="프로필 이미지 경로")
    known_for_department: Optional[str] = Field(default=None, description="주요 활동 분야")


class UserSearchResult(BaseModel):
    """사용자 검색 결과"""

    user_id: Optional[int] = Field(default=None, description="사용자 ID")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")

    class Config:
        from_attributes = True


SearchResult = Union[MovieSearchResult, PersonSearchResult, UserSearchResult]


class SearchResponse(BaseModel):
    """통합 검색 응답"""

    movies: List[MovieSearchResult] = Field(description="영화 검색 결과")
    persons: List[PersonSearchResult] = Field(description="인물 검색 결과")
    users: List[UserSearchResult] = Field(description="사용자 검색 결과")
    movie_count: int = Field(description="영화 결과 수")
    person_count: int = Field(description="인물 결과 수")
    user_count: int = Field(description="사용자 결과 수")
