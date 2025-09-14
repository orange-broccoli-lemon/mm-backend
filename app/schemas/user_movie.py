# app/schemas/user_movie.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

class WatchStatus(str, Enum):
    watching = "watching"
    completed = "completed"
    plan_to_watch = "plan_to_watch"
    dropped = "dropped"

class UserMovie(BaseModel):
    user_movie_id: Optional[int] = Field(default=None, description="사용자 영화 ID")
    user_id: int = Field(description="사용자 ID")
    movie_id: int = Field(description="영화 ID")
    status: WatchStatus = Field(default=WatchStatus.completed, description="시청 상태")
    rating: Optional[Decimal] = Field(default=None, description="평점", ge=0, le=10)
    watched_date: Optional[date] = Field(default=None, description="시청일")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    
    class Config:
        from_attributes = True
