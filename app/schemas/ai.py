from typing import Optional
from pydantic import BaseModel, Field


class FindBotRequest(BaseModel):
    query: str = Field(description="영화를 찾기 위한 단서", min_length=1, max_length=1000)


class FindBotResponse(BaseModel):
    success: bool = Field(description="영화 찾기 성공 여부")
    title: Optional[str] = Field(default=None, description="영화 제목")
    movie_id: Optional[int] = Field(default=None, description="TMDB 영화 ID")
    reason: Optional[str] = Field(default=None, description="추측 근거")
    plot: Optional[str] = Field(default=None, description="줄거리")
    message: Optional[str] = Field(default=None, description="실패 메시지")

    class Config:
        exclude_none = True
