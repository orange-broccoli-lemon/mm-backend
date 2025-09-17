# app/schemas/search.py

from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import date


class MovieSearchResult(BaseModel):
    """영화 검색 결과"""

    id: int = Field(description="TMDB 영화 ID")
    media_type: Literal["movie"] = "movie"
    title: str = Field(description="영화 제목")
    overview: Optional[str] = Field(default=None, description="줄거리")
    release_date: Optional[date] = Field(default=None, description="개봉일")
    poster_path: Optional[str] = Field(default=None, description="포스터 경로")
    vote_average: float = Field(description="평점")


class PersonSearchResult(BaseModel):
    """인물 검색 결과"""

    id: int = Field(description="TMDB 인물 ID")
    media_type: Literal["person"] = "person"
    name: str = Field(description="인물 이름")
    profile_path: Optional[str] = Field(default=None, description="프로필 이미지 경로")

class UserSearchResult(BaseModel):
    user_id: Optional[int] = Field(default=None, description="사용자 ID")
    google_id: Optional[str] = Field(default=None, description="구글 ID")
    email: str = Field(description="이메일")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    is_active: bool = Field(default=True, description="활성 상태")

    class Config:
        from_attributes = True

# 검색 결과 타입
SearchResult = Union[MovieSearchResult, PersonSearchResult, UserSearchResult]


class SearchResponse(BaseModel):
    """통합 검색 응답"""

    results: List[SearchResult] = Field(description="검색 결과")
