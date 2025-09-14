# app/schemas/user.py

from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

class User(BaseModel):
    user_id: Optional[int] = Field(default=None, description="사용자 ID")
    google_id: str = Field(description="구글 ID")
    email: EmailStr = Field(description="이메일")
    name: str = Field(description="사용자 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    last_login: Optional[datetime] = Field(default=None, description="마지막 로그인")
    is_active: bool = Field(default=True, description="활성 상태")
    
    class Config:
        from_attributes = True
