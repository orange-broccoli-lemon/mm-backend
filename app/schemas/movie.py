# app/schemas/movie.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal


class Movie(BaseModel):
    movie_id: int = Field(description="TMDB 영화 ID")
    title: str = Field(description="영화 제목")
    original_title: Optional[str] = Field(default=None, description="원제")
    overview: Optional[str] = Field(default=None, description="줄거리")
    release_date: Optional[date] = Field(default=None, description="개봉일")
    runtime: Optional[int] = Field(default=None, description="상영시간(분)")
    poster_url: Optional[str] = Field(default=None, description="포스터 URL")
    backdrop_url: Optional[str] = Field(default=None, description="배경 이미지 URL")
    average_rating: Decimal = Field(default=0.00, description="평균 평점")
    is_adult: bool = Field(default=False, description="성인 영화 여부")
    trailer_url: Optional[str] = Field(default=None, description="트레일러 URL")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    concise_review: Optional[str] = Field(default=None, description="AI 리뷰 요약")
    concise_review_date: Optional[datetime] = Field(default=None, description="리뷰 분석 일시")

    class Config:
        from_attributes = True


class MovieLike(BaseModel):
    user_id: int = Field(description="사용자 ID")
    movie_id: int = Field(description="영화 ID")
    created_at: Optional[datetime] = Field(default=None, description="좋아요 날짜")

    class Config:
        from_attributes = True


class Watchlist(BaseModel):
    user_id: int = Field(description="사용자 ID")
    movie_id: int = Field(description="영화 ID")
    created_at: Optional[datetime] = Field(default=None, description="추가 날짜")

    class Config:
        from_attributes = True


class WatchlistMovie(BaseModel):
    """왓치리스트 목록용 영화 정보"""

    movie_id: int = Field(description="영화 ID")
    title: str = Field(description="영화 제목")
    poster_url: Optional[str] = Field(default=None, description="포스터 URL")
    release_date: Optional[date] = Field(default=None, description="개봉일")
    average_rating: Decimal = Field(description="평균 평점")
    added_at: datetime = Field(description="왓치리스트 추가일")

    class Config:
        from_attributes = True
