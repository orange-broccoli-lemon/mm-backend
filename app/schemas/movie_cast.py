# app/schemas/movie_cast.py

from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

class CastRole(str, Enum):
    cast = "cast"
    director = "director"
    crew = "crew"

class MovieCast(BaseModel):
    movie_cast_id: Optional[int] = Field(default=None, description="영화 캐스트 ID")
    movie_id: int = Field(description="영화 ID")
    actor_id: int = Field(description="배우 ID")
    character_name: Optional[str] = Field(default=None, description="캐릭터명")
    role: CastRole = Field(default=CastRole.cast, description="역할")
    
    class Config:
        from_attributes = True
