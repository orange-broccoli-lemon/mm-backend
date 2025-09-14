# app/schemas/user.py

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

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
