# app/schemas/user.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
from app.schemas.movie import WatchlistMovie

class User(BaseModel):
    user_id: Optional[int] = Field(default=None, description="사용자 ID")
    google_id: Optional[str] = Field(default=None, description="구글 ID")
    email: str = Field(description="이메일")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    last_login: Optional[datetime] = Field(default=None, description="마지막 로그인")
    is_active: bool = Field(default=True, description="활성 상태")

    class Config:
        from_attributes = True

class UserCreateEmail(BaseModel):
    email: str = Field(description="이메일")
    password: str = Field(description="비밀번호", min_length=6)
    name: str = Field(description="사용자 이름", min_length=2)
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")

class UserCreateGoogle(BaseModel):
    google_id: str = Field(description="구글 ID")
    email: str = Field(description="이메일")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")

class UserLoginEmail(BaseModel):
    email: str = Field(description="이메일")
    password: str = Field(description="비밀번호")

class UserLoginGoogle(BaseModel):
    google_id: str = Field(description="구글 ID")
    email: str = Field(description="이메일")

class EmailCheck(BaseModel):
    email: str = Field(description="확인할 이메일")

class TokenResponse(BaseModel):
    access_token: str = Field(description="액세스 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")
    user: User = Field(description="사용자 정보")

class UserComment(BaseModel):
    """사용자 상세 페이지에서 보여줄 코멘트 정보"""
    comment_id: int = Field(description="댓글 ID")
    movie_id: int = Field(description="영화 ID")
    content: str = Field(description="댓글 내용")
    is_spoiler: bool = Field(description="스포일러 여부")
    likes_count: int = Field(description="좋아요 수")
    created_at: datetime = Field(description="작성일시")

    class Config:
        from_attributes = True

class UserFollower(BaseModel):
    """팔로워 정보"""
    user_id: int = Field(description="사용자 ID")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    created_at: datetime = Field(description="팔로우 시작일")

    class Config:
        from_attributes = True

class UserFollowing(BaseModel):
    """팔로잉 정보"""
    user_id: int = Field(description="사용자 ID")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    created_at: datetime = Field(description="팔로우 시작일")

    class Config:
        from_attributes = True

class UserFollowingPerson(BaseModel):
    """팔로우 중인 인물 정보"""
    person_id: int = Field(description="인물 ID")
    name: str = Field(description="인물 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    created_at: datetime = Field(description="팔로우 시작일")

    class Config:
        from_attributes = True

class UserDetail(BaseModel):
    """사용자 상세 정보"""
    # 기본 사용자 정보
    user_id: int = Field(description="사용자 ID")
    email: Optional[str] = Field(default=None, description="이메일 (본인만 조회 가능)")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    created_at: datetime = Field(description="가입일시")
    last_login: Optional[datetime] = Field(default=None, description="마지막 로그인 (본인만 조회 가능)")
    is_active: bool = Field(description="활성 상태")

    # 통계
    followers_count: int = Field(default=0, description="팔로워 수")
    following_count: int = Field(default=0, description="팔로잉 수")
    following_persons_count: int = Field(default=0, description="팔로우 중인 인물 수")
    comments_count: int = Field(default=0, description="작성한 코멘트 수")
    liked_movies_count: int = Field(default=0, description="좋아요한 영화 수")
    watchlist_count: int = Field(default=0, description="왓치리스트 영화 수")

    class Config:
        from_attributes = True