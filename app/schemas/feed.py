# app/schemas/feed.py

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class FeedComment(BaseModel):
    comment_id: int = Field(description="댓글 ID")
    movie_id: int = Field(description="영화 ID")
    content: str = Field(description="댓글 내용")
    is_spoiler: bool = Field(description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(default=None, description="스포일러 신뢰도")
    likes_count: int = Field(description="좋아요 수")
    is_liked: bool = Field(description="현재 사용자 좋아요 여부")
    created_at: datetime = Field(description="댓글 작성일")

    # 작성자 정보
    author_id: int = Field(description="작성자 ID")
    author_name: str = Field(description="작성자 이름")
    author_profile_image: Optional[str] = Field(default=None, description="작성자 프로필 이미지")

    # 영화 정보
    movie_title: str = Field(description="영화 제목")
    movie_poster_url: Optional[str] = Field(default=None, description="영화 포스터 URL")
    movie_release_date: Optional[str] = Field(default=None, description="영화 개봉일")

    class Config:
        from_attributes = True


class FeedResponse(BaseModel):
    comments: List[FeedComment] = Field(description="피드 댓글 목록")
    total: int = Field(description="총 댓글 수")
    has_next: bool = Field(description="다음 페이지 존재 여부")


class FeedFilter(BaseModel):
    include_spoilers: bool = Field(default=True, description="스포일러 댓글 포함 여부")
    movie_ids: Optional[List[int]] = Field(default=None, description="특정 영화 ID 필터")
    days_ago: Optional[int] = Field(default=None, description="N일 이내 댓글만 조회")
