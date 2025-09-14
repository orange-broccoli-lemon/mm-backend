# app/schemas/genre.py

from typing import List
from pydantic import BaseModel, Field

class Genre(BaseModel):
    id: int = Field(description="장르 ID")
    name: str = Field(description="장르 이름")

class GenreListResponse(BaseModel):
    genres: List[Genre] = Field(description="장르 목록")
