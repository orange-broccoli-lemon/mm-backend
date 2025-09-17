# app/schemas/user_follow.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class UserFollow(BaseModel):
    follower_id: int = Field(description="팔로워 ID")
    following_id: int = Field(description="팔로잉 ID")
    created_at: Optional[datetime] = Field(default=None, description="팔로우 시작일")

    class Config:
        from_attributes = True


class FollowRequest(BaseModel):
    following_id: int = Field(description="팔로우할 사용자 ID")


class FollowStats(BaseModel):
    user_id: int = Field(description="사용자 ID")
    followers_count: int = Field(description="팔로워 수")
    following_count: int = Field(description="팔로잉 수")


class FollowUser(BaseModel):
    user_id: int = Field(description="사용자 ID")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    is_following: bool = Field(description="현재 사용자가 팔로우 중인지 여부")
    created_at: Optional[datetime] = Field(
        default=None, description="팔로우 시작일 (팔로잉 목록일 때)"
    )


class FollowListResponse(BaseModel):
    users: list[FollowUser] = Field(description="사용자 목록")
    total: int = Field(description="총 사용자 수")
