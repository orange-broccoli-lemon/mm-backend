# app/schemas/comment.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal

class Comment(BaseModel):
    comment_id: Optional[int] = Field(default=None, description="댓글 ID")
    movie_id: int = Field(description="TMDB 영화 ID")
    user_id: int = Field(description="사용자 ID")
    content: str = Field(description="댓글 내용")
    rating: Optional[Decimal] = Field(default=None, description="평점 (0.0 ~ 10.0)")
    watched_date: Optional[date] = Field(default=None, description="시청 날짜")
    is_spoiler: bool = Field(default=False, description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(default=None, description="스포일러 신뢰도")
    is_public: bool = Field(default=True, description="공개 여부")
    likes_count: int = Field(default=0, description="좋아요 수")
    is_liked: bool = Field(default=False, description="현재 사용자 좋아요 여부")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    
    # 사용자 정보 (조회시 포함)
    user_name: Optional[str] = Field(default=None, description="작성자 이름")
    user_profile_image: Optional[str] = Field(default=None, description="작성자 프로필 이미지")
    
    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    movie_id: int = Field(description="TMDB 영화 ID")
    content: str = Field(description="댓글 내용", min_length=1, max_length=1000)
    rating: Optional[Decimal] = Field(
        default=None, 
        description="평점 (0.0 ~ 10.0)", 
        ge=0.0, 
        le=10.0
    )
    watched_date: Optional[date] = Field(default=None, description="시청 날짜")
    is_spoiler: bool = Field(default=False, description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(
        default=None, 
        description="스포일러 신뢰도 (0.0 ~ 1.0)", 
        ge=0.0, 
        le=1.0
    )
    is_public: bool = Field(default=True, description="공개 여부")


class CommentUpdate(BaseModel):
    content: Optional[str] = Field(default=None, description="댓글 내용", min_length=1, max_length=1000)
    rating: Optional[Decimal] = Field(
        default=None, 
        description="평점 (0.0 ~ 10.0)", 
        ge=0.0, 
        le=10.0
    )
    watched_date: Optional[date] = Field(default=None, description="시청 날짜")
    is_spoiler: Optional[bool] = Field(default=None, description="스포일러 여부")
    spoiler_confidence: Optional[Decimal] = Field(
        default=None, 
        description="스포일러 신뢰도 (0.0 ~ 1.0)", 
        ge=0.0, 
        le=1.0
    )
    is_public: Optional[bool] = Field(default=None, description="공개 여부")


class CommentLike(BaseModel):
    user_id: int = Field(description="사용자 ID")
    comment_id: int = Field(description="댓글 ID")
    created_at: Optional[datetime] = Field(default=None, description="좋아요 날짜")
    
    class Config:
        from_attributes = True


class CommentLikeRequest(BaseModel):
    comment_id: int = Field(description="좋아요할 댓글 ID")


class CommentWithMovie(BaseModel):
    """영화 정보가 포함된 댓글"""
    comment_id: int = Field(description="댓글 ID")
    content: str = Field(description="댓글 내용")
    rating: Optional[Decimal] = Field(default=None, description="평점")
    watched_date: Optional[date] = Field(default=None, description="시청 날짜")
    is_spoiler: bool = Field(description="스포일러 여부")
    is_public: bool = Field(description="공개 여부")
    likes_count: int = Field(description="좋아요 수")
    created_at: datetime = Field(description="작성일시")
    
    # 영화 정보
    movie_id: int = Field(description="영화 ID")
    movie_title: str = Field(description="영화 제목")
    movie_poster_url: Optional[str] = Field(default=None, description="영화 포스터")
    movie_release_date: Optional[date] = Field(default=None, description="영화 개봉일")
    
    class Config:
        from_attributes = True
