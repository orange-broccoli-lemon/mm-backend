from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

class Movie(BaseModel):
    """영화 정보 모델 (movies 테이블 구조 기반)"""
    tmdb_id: int = Field(description="TMDB 영화 ID")
    title: str = Field(description="영화 제목 (한국어)")
    original_title: str = Field(description="원제")
    overview: Optional[str] = Field(default=None, description="영화 줄거리")
    release_date: Optional[date] = Field(default=None, description="개봉일")
    runtime: Optional[int] = Field(default=None, description="상영시간 (분)")
    poster_url: Optional[str] = Field(default=None, description="포스터 이미지 URL")
    backdrop_url: Optional[str] = Field(default=None, description="배경 이미지 URL")
    average_rating: float = Field(default=0.0, description="평균 평점")
    is_adult: bool = Field(default=False, description="성인 영화 여부")
    trailer_url: Optional[str] = Field(default=None, description="트레일러 URL")
    vote_average: float = Field(description="TMDB 평점 평균")
    vote_count: int = Field(description="TMDB 투표 수")
    popularity: float = Field(description="TMDB 인기도")
    genre_ids: List[int] = Field(default_factory=list, description="장르 ID 목록")
    original_language: str = Field(description="원어")
