# app/api/v1/feed.py

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.feed import FeedResponse, FeedFilter
from app.schemas.user import User
from app.schemas.person import PersonFeedResponse
from app.services.feed_service import FeedService
from app.services.person_service import PersonService
from app.core.dependencies import get_current_user

router = APIRouter()


def get_feed_service() -> FeedService:
    return FeedService()


@router.get(
    "/following",
    response_model=FeedResponse,
    summary="팔로잉 피드",
    description="팔로우한 사용자들의 댓글을 시간순으로 조회합니다.",
)
async def get_following_feed(
    skip: int = Query(default=0, ge=0, description="건너뛸 댓글 수"),
    limit: int = Query(default=20, ge=1, le=50, description="가져올 댓글 수"),
    include_spoilers: bool = Query(default=True, description="스포일러 댓글 포함 여부"),
    movie_ids: Optional[str] = Query(default=None, description="특정 영화 ID 필터 (쉼표로 구분)"),
    days_ago: Optional[int] = Query(default=None, ge=1, le=30, description="N일 이내 댓글만 조회"),
    current_user: User = Depends(get_current_user),
    feed_service: FeedService = Depends(get_feed_service),
):
    try:
        # 필터 생성
        feed_filter = FeedFilter(include_spoilers=include_spoilers, days_ago=days_ago)

        # movie_ids 파싱
        if movie_ids:
            try:
                feed_filter.movie_ids = [int(id.strip()) for id in movie_ids.split(",")]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid movie_ids format")

        feed = await feed_service.get_user_feed(current_user.user_id, skip, limit, feed_filter)
        return feed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/trending",
    response_model=FeedResponse,
    summary="트렌딩 피드",
    description="최근 인기 댓글을 좋아요 순으로 조회합니다.",
)
async def get_trending_feed(
    skip: int = Query(default=0, ge=0, description="건너뛸 댓글 수"),
    limit: int = Query(default=20, ge=1, le=50, description="가져올 댓글 수"),
    hours_ago: int = Query(default=24, ge=1, le=168, description="N시간 이내 댓글만 조회"),
    current_user: User = Depends(get_current_user),
    feed_service: FeedService = Depends(get_feed_service),
):
    try:
        feed = await feed_service.get_trending_feed(current_user.user_id, skip, limit, hours_ago)
        return feed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/movie/{movie_id}",
    response_model=FeedResponse,
    summary="영화별 피드",
    description="특정 영화의 모든 댓글을 조회합니다 (팔로잉 여부 무관).",
)
async def get_movie_feed(
    movie_id: int,
    skip: int = Query(default=0, ge=0, description="건너뛸 댓글 수"),
    limit: int = Query(default=20, ge=1, le=50, description="가져올 댓글 수"),
    include_spoilers: bool = Query(default=True, description="스포일러 댓글 포함 여부"),
    current_user: User = Depends(get_current_user),
    feed_service: FeedService = Depends(get_feed_service),
):
    try:
        feed_filter = FeedFilter(include_spoilers=include_spoilers, movie_ids=[movie_id])

        # 모든 사용자의 댓글을 보기 위해 특별한 메서드 사용
        feed = await feed_service.get_user_feed(current_user.user_id, skip, limit, feed_filter)
        return feed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_person_service() -> PersonService:
    return PersonService()


@router.get(
    "/persons",
    response_model=PersonFeedResponse,
    summary="팔로우한 인물 피드",
    description="팔로우한 인물들의 새로운 작품 활동을 조회합니다.",
)
async def get_followed_persons_feed(
    skip: int = Query(default=0, ge=0, description="건너뛸 아이템 수"),
    limit: int = Query(default=20, ge=1, le=50, description="가져올 아이템 수"),
    current_user: User = Depends(get_current_user),
    person_service: PersonService = Depends(get_person_service),
):
    try:
        feed = await person_service.get_followed_persons_feed(current_user.user_id, skip, limit)
        return feed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
