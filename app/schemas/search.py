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


# 검색 결과 타입
SearchResult = Union[MovieSearchResult, PersonSearchResult]


class SearchResponse(BaseModel):
    """통합 검색 응답"""

    results: List[SearchResult] = Field(description="검색 결과")
