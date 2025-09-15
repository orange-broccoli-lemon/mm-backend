# app/schemas/genre.py

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class Genre(BaseModel):
    genre_id: int = Field(description="장르 ID")
    name: str = Field(description="장르 이름")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    
    class Config:
        from_attributes = True

class GenreWithMovieCount(BaseModel):
    genre_id: int = Field(description="장르 ID")
    name: str = Field(description="장르 이름")
    movie_count: int = Field(description="해당 장르의 영화 수")
    
    class Config:
        from_attributes = True

class GenreListResponse(BaseModel):
    genres: List[Genre] = Field(description="장르 목록")

class GenreMovieListResponse(BaseModel):
    genre: Genre = Field(description="장르 정보")
    movies: List = Field(description="영화 목록")
    total: int = Field(description="총 영화 수")

class GenreStatsResponse(BaseModel):
    genres: List[GenreWithMovieCount] = Field(description="장르별 통계")
    total_genres: int = Field(description="총 장르 수")
