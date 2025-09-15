# app/api/v1/follows.py

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from app.schemas.user_follow import UserFollow, FollowRequest, FollowStats, FollowListResponse
from app.schemas.user import User
from app.services.user_follow_service import UserFollowService
from app.core.dependencies import get_current_user

router = APIRouter()

def get_follow_service() -> UserFollowService:
    return UserFollowService()

@router.post(
    "/",
    response_model=UserFollow,
    summary="사용자 팔로우",
    description="다른 사용자를 팔로우합니다."
)
async def follow_user(
    follow_request: FollowRequest,
    current_user: User = Depends(get_current_user),
    follow_service: UserFollowService = Depends(get_follow_service)
):
    try:
        follow = await follow_service.follow_user(current_user.user_id, follow_request.following_id)
        return follow
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete(
    "/{following_id}",
    summary="사용자 언팔로우",
    description="팔로우 중인 사용자를 언팔로우합니다."
)
async def unfollow_user(
    following_id: int = Path(description="언팔로우할 사용자 ID"),
    current_user: User = Depends(get_current_user),
    follow_service: UserFollowService = Depends(get_follow_service)
):
    try:
        success = await follow_service.unfollow_user(current_user.user_id, following_id)
        return {"message": "언팔로우가 완료되었습니다", "success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/stats/{user_id}",
    response_model=FollowStats,
    summary="팔로우 통계",
    description="사용자의 팔로워/팔로잉 수를 조회합니다."
)
async def get_follow_stats(
    user_id: int = Path(description="사용자 ID"),
    follow_service: UserFollowService = Depends(get_follow_service)
):
    try:
        stats = await follow_service.get_follow_stats(user_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{user_id}/followers",
    response_model=FollowListResponse,
    summary="팔로워 목록",
    description="사용자의 팔로워 목록을 조회합니다."
)
async def get_followers(
    user_id: int = Path(description="사용자 ID"),
    skip: int = Query(default=0, ge=0, description="건너뛸 사용자 수"),
    limit: int = Query(default=20, ge=1, le=100, description="가져올 사용자 수"),
    current_user: Optional[User] = Depends(get_current_user),
    follow_service: UserFollowService = Depends(get_follow_service)
):
    try:
        current_user_id = current_user.user_id if current_user else None
        followers = await follow_service.get_followers(user_id, current_user_id, skip, limit)
        return followers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{user_id}/following",
    response_model=FollowListResponse,
    summary="팔로잉 목록",
    description="사용자가 팔로우하는 사람들의 목록을 조회합니다."
)
async def get_following(
    user_id: int = Path(description="사용자 ID"),
    skip: int = Query(default=0, ge=0, description="건너뛸 사용자 수"),
    limit: int = Query(default=20, ge=1, le=100, description="가져올 사용자 수"),
    current_user: Optional[User] = Depends(get_current_user),
    follow_service: UserFollowService = Depends(get_follow_service)
):
    try:
        current_user_id = current_user.user_id if current_user else None
        following = await follow_service.get_following(user_id, current_user_id, skip, limit)
        return following
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/check/{following_id}",
    summary="팔로우 관계 확인",
    description="현재 사용자가 특정 사용자를 팔로우하는지 확인합니다."
)
async def check_follow_relationship(
    following_id: int = Path(description="확인할 사용자 ID"),
    current_user: User = Depends(get_current_user),
    follow_service: UserFollowService = Depends(get_follow_service)
):
    try:
        is_following = await follow_service.is_following(current_user.user_id, following_id)
        return {"is_following": is_following}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
