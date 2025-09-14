# app/schemas/comment.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class Comment(BaseModel):
    comment_id: Optional[int] = Field(default=None, description="댓글 ID")
    movie_id: int = Field(description="TMDB 영화 ID")
    user_id: int = Field(description="사용자 ID")
    content: str = Field(description="댓글 내용")
    is_spoiler: bool = Field(default=False, description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(default=None, description="스포일러 신뢰도")
    likes_count: int = Field(default=0, description="좋아요 수")
    is_liked: bool = Field(default=False, description="현재 사용자 좋아요 여부")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    movie_id: int = Field(description="TMDB 영화 ID")
    content: str = Field(description="댓글 내용", min_length=1, max_length=1000)
    is_spoiler: bool = Field(default=False, description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(default=None, description="스포일러 신뢰도", ge=0, le=1)

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(default=None, description="댓글 내용", min_length=1, max_length=1000)
    is_spoiler: Optional[bool] = Field(default=None, description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(default=None, description="스포일러 신뢰도", ge=0, le=1)
