# app/api/v1/persons.py

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from app.schemas.person import (
    Person, PersonFollow, PersonFollowRequest, PersonCreditsResponse, 
    PersonFeedResponse
)
from app.schemas.user import User
from app.services.person_service import PersonService
from app.core.dependencies import get_current_user, get_optional_current_user
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

def get_person_service() -> PersonService:
    return PersonService()

@router.get(
    "/{person_id}",
    response_model=Person,
    summary="인물 상세 정보",
    description="특정 인물의 상세 정보를 조회합니다."
)
async def get_person_by_id(
    person_id: int = Path(description="인물 ID"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    person_service: PersonService = Depends(get_person_service)
):
    try:
        current_user_id = current_user.user_id if current_user else None
        person = await person_service.get_person_by_id(person_id, current_user_id)
        if not person:
            raise HTTPException(status_code=404, detail="인물을 찾을 수 없습니다")
        return person
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/{person_id}/follow",
    response_model=PersonFollow,
    summary="인물 팔로우",
    description="특정 인물을 팔로우합니다."
)
async def follow_person(
    person_id: int = Path(description="팔로우할 인물 ID"),
    current_user: User = Depends(get_current_user),
    person_service: PersonService = Depends(get_person_service)
):
    try:
        follow = await person_service.follow_person(current_user.user_id, person_id)
        return follow
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete(
    "/{person_id}/follow",
    summary="인물 언팔로우",
    description="팔로우 중인 인물을 언팔로우합니다."
)
async def unfollow_person(
    person_id: int = Path(description="언팔로우할 인물 ID"),
    current_user: User = Depends(get_current_user),
    person_service: PersonService = Depends(get_person_service)
):
    try:
        success = await person_service.unfollow_person(current_user.user_id, person_id)
        return {"message": "언팔로우가 완료되었습니다", "success": success}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get(
    "/{person_id}/credits",
    response_model=PersonCreditsResponse,
    summary="인물 출연작품",
    description="인물의 출연 및 참여 작품 목록을 조회합니다."
)
async def get_person_credits(
    person_id: int = Path(description="인물 ID"),
    person_service: PersonService = Depends(get_person_service)
):
    try:
        credits = await person_service.get_person_credits(person_id)
        return credits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/search",
    response_model=List[Person],
    summary="인물 검색",
    description="인물 이름으로 검색합니다."
)
async def search_persons(
    query: str = Query(description="검색할 인물 이름"),
    skip: int = Query(default=0, ge=0, description="건너뛸 인물 수"),
    limit: int = Query(default=20, ge=1, le=50, description="가져올 인물 수"),
    person_service: PersonService = Depends(get_person_service)
):
    try:
        persons = await person_service.search_persons(query, skip, limit)
        return persons
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get(
    "/", 
    response_model=list[Person],
    summary="DB 전체 인물 조회 (개발용)",
    description="개발용 엔드포인트입니다. DB에 저장된 모든 인물 목록을 조회합니다."
)
async def get_all_persons(db: Session = Depends(get_db)):
    """DB 전체 인물 조회"""
    person_service = PersonService()
    
    try:
        persons = await person_service.get_all_persons()
        return persons
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
