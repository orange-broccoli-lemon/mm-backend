# app/schemas/comment.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class Comment(BaseModel):
    comment_id: Optional[int] = Field(default=None, description="댓글 ID")
    movie_id: int = Field(description="영화 ID")
    user_id: int = Field(description="사용자 ID")
    content: str = Field(description="댓글 내용")
    is_spoiler: bool = Field(default=False, description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(default=None, description="스포일러 신뢰도")
    parent_comment_id: Optional[int] = Field(default=None, description="부모 댓글 ID")
    likes_count: int = Field(default=0, description="좋아요 수")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    
    class Config:
        from_attributes = True
