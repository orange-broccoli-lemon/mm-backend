# app/schemas/person.py

from typing import Optional
from pydantic import BaseModel, Field

class Person(BaseModel):
    person_id: Optional[int] = Field(default=None, description="인물 ID")
    name: str = Field(description="인물 이름")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    
    class Config:
        from_attributes = True
