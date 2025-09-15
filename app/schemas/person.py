# app/schemas/person.py

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import IntEnum

class Gender(IntEnum):
    UNKNOWN = 0
    FEMALE = 1
    MALE = 2

class Person(BaseModel):
    person_id: int = Field(description="인물 ID")
    name: str = Field(description="이름")
    original_name: Optional[str] = Field(default=None, description="원래 이름")
    biography: Optional[str] = Field(default=None, description="전기")
    birthday: Optional[date] = Field(default=None, description="생일")
    deathday: Optional[date] = Field(default=None, description="사망일")
    place_of_birth: Optional[str] = Field(default=None, description="출생지")
    profile_image_url: Optional[str] = Field(default=None, description="프로필 이미지 URL")
    gender: Optional[Gender] = Field(default=Gender.UNKNOWN, description="성별")
    known_for_department: Optional[str] = Field(default=None, description="주요 활동 분야")
    popularity: int = Field(default=0, description="인기도")
    is_adult: bool = Field(default=False, description="성인 인물 여부")
    is_following: bool = Field(default=False, description="현재 사용자 팔로우 여부")
    followers_count: int = Field(default=0, description="팔로워 수")
    created_at: Optional[datetime] = Field(default=None, description="생성일시")
    updated_at: Optional[datetime] = Field(default=None, description="수정일시")
    
    class Config:
        from_attributes = True

class PersonFollow(BaseModel):
    user_id: int = Field(description="사용자 ID")
    person_id: int = Field(description="인물 ID")
    created_at: Optional[datetime] = Field(default=None, description="팔로우 시작일")
    
    class Config:
        from_attributes = True

class PersonFollowRequest(BaseModel):
    person_id: int = Field(description="팔로우할 인물 ID")

class PersonStats(BaseModel):
    person_id: int = Field(description="인물 ID")
    followers_count: int = Field(description="팔로워 수")
    movies_count: int = Field(description="참여 영화 수")

class MovieCredit(BaseModel):
    movie_id: int = Field(description="영화 ID")
    movie_title: str = Field(description="영화 제목")
    movie_poster_url: Optional[str] = Field(default=None, description="영화 포스터")
    release_date: Optional[date] = Field(default=None, description="개봉일")
    character_name: Optional[str] = Field(default=None, description="배역명")
    job: Optional[str] = Field(default=None, description="역할")
    department: Optional[str] = Field(default=None, description="부서")
    is_main_cast: bool = Field(default=False, description="주연 여부")

class PersonCreditsResponse(BaseModel):
    person: Person = Field(description="인물 정보")
    acting_credits: List[MovieCredit] = Field(description="출연 작품")
    crew_credits: List[MovieCredit] = Field(description="스태프 참여 작품")
    total_movies: int = Field(description="총 참여 영화 수")

class PersonFeedItem(BaseModel):
    movie_id: int = Field(description="영화 ID")
    movie_title: str = Field(description="영화 제목")
    movie_poster_url: Optional[str] = Field(default=None, description="영화 포스터")
    release_date: Optional[date] = Field(default=None, description="개봉일")
    person_id: int = Field(description="인물 ID")
    person_name: str = Field(description="인물 이름")
    person_profile_image: Optional[str] = Field(default=None, description="인물 프로필 이미지")
    character_name: Optional[str] = Field(default=None, description="배역명")
    job: Optional[str] = Field(default=None, description="역할")
    is_main_cast: bool = Field(default=False, description="주연 여부")
    activity_type: str = Field(description="활동 타입", default="movie_credit")

class PersonFeedResponse(BaseModel):
    items: List[PersonFeedItem] = Field(description="피드 아이템 목록")
    total: int = Field(description="총 아이템 수")
    has_next: bool = Field(description="다음 페이지 존재 여부")
