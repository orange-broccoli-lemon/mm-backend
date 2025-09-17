# app/services/user_follow_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from app.models.user_follow import UserFollowModel
from app.models.user import UserModel
from app.schemas.user_follow import UserFollow, FollowStats, FollowUser, FollowListResponse
from app.database import get_db


class UserFollowService:

    def __init__(self):
        self.db: Session = next(get_db())

    async def follow_user(self, follower_id: int, following_id: int) -> UserFollow:
        """사용자 팔로우"""
        try:
            # 자기 자신 팔로우 방지
            if follower_id == following_id:
                raise Exception("자기 자신을 팔로우할 수 없습니다")

            # 팔로우할 사용자 존재 확인
            following_user_stmt = select(UserModel).where(UserModel.user_id == following_id)
            following_user_result = self.db.execute(following_user_stmt)
            following_user = following_user_result.scalar_one_or_none()

            if not following_user:
                raise Exception("팔로우할 사용자를 찾을 수 없습니다")

            # 이미 팔로우 중인지 확인
            existing_follow_stmt = select(UserFollowModel).where(
                and_(
                    UserFollowModel.follower_id == follower_id,
                    UserFollowModel.following_id == following_id,
                )
            )
            existing_follow_result = self.db.execute(existing_follow_stmt)
            existing_follow = existing_follow_result.scalar_one_or_none()

            if existing_follow:
                raise Exception("이미 팔로우 중인 사용자입니다")

            # 새 팔로우 관계 생성
            new_follow = UserFollowModel(follower_id=follower_id, following_id=following_id)

            self.db.add(new_follow)
            self.db.commit()
            self.db.refresh(new_follow)

            return UserFollow(
                follower_id=new_follow.follower_id,
                following_id=new_follow.following_id,
                created_at=new_follow.created_at,
            )

        except Exception as e:
            self.db.rollback()
            raise Exception(f"팔로우 실패: {str(e)}")

    async def unfollow_user(self, follower_id: int, following_id: int) -> bool:
        """사용자 언팔로우"""
        try:
            follow_stmt = select(UserFollowModel).where(
                and_(
                    UserFollowModel.follower_id == follower_id,
                    UserFollowModel.following_id == following_id,
                )
            )
            follow_result = self.db.execute(follow_stmt)
            follow = follow_result.scalar_one_or_none()

            if not follow:
                raise Exception("팔로우 관계를 찾을 수 없습니다")

            self.db.delete(follow)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"언팔로우 실패: {str(e)}")

    async def get_follow_stats(self, user_id: int) -> FollowStats:
        """사용자의 팔로우 통계"""
        try:
            # 팔로워 수
            followers_stmt = select(func.count(UserFollowModel.follower_id)).where(
                UserFollowModel.following_id == user_id
            )
            followers_result = self.db.execute(followers_stmt)
            followers_count = followers_result.scalar() or 0

            # 팔로잉 수
            following_stmt = select(func.count(UserFollowModel.following_id)).where(
                UserFollowModel.follower_id == user_id
            )
            following_result = self.db.execute(following_stmt)
            following_count = following_result.scalar() or 0

            return FollowStats(
                user_id=user_id, followers_count=followers_count, following_count=following_count
            )

        except Exception as e:
            raise Exception(f"팔로우 통계 조회 실패: {str(e)}")

    async def get_followers(
        self, user_id: int, current_user_id: Optional[int] = None, skip: int = 0, limit: int = 20
    ) -> FollowListResponse:
        """팔로워 목록 조회"""
        try:
            # 팔로워 목록 쿼리
            stmt = (
                select(
                    UserModel.user_id,
                    UserModel.name,
                    UserModel.profile_image_url,
                    UserFollowModel.created_at,
                )
                .join(UserFollowModel, UserModel.user_id == UserFollowModel.follower_id)
                .where(UserFollowModel.following_id == user_id)
                .offset(skip)
                .limit(limit)
            )

            result = self.db.execute(stmt)
            followers_data = result.all()

            followers = []
            for user_id_val, name, profile_image_url, created_at in followers_data:
                # 현재 사용자가 이 팔로워를 팔로우하는지 확인
                is_following = False
                if current_user_id:
                    is_following = await self._is_following(current_user_id, user_id_val)

                followers.append(
                    FollowUser(
                        user_id=user_id_val,
                        name=name,
                        profile_image_url=profile_image_url,
                        is_following=is_following,
                        created_at=created_at,
                    )
                )

            # 총 팔로워 수
            total_stmt = select(func.count(UserFollowModel.follower_id)).where(
                UserFollowModel.following_id == user_id
            )
            total_result = self.db.execute(total_stmt)
            total = total_result.scalar() or 0

            return FollowListResponse(users=followers, total=total)

        except Exception as e:
            raise Exception(f"팔로워 목록 조회 실패: {str(e)}")

    async def get_following(
        self, user_id: int, current_user_id: Optional[int] = None, skip: int = 0, limit: int = 20
    ) -> FollowListResponse:
        """팔로잉 목록 조회"""
        try:
            # 팔로잉 목록 쿼리
            stmt = (
                select(
                    UserModel.user_id,
                    UserModel.name,
                    UserModel.profile_image_url,
                    UserFollowModel.created_at,
                )
                .join(UserFollowModel, UserModel.user_id == UserFollowModel.following_id)
                .where(UserFollowModel.follower_id == user_id)
                .offset(skip)
                .limit(limit)
            )

            result = self.db.execute(stmt)
            following_data = result.all()

            following = []
            for user_id_val, name, profile_image_url, created_at in following_data:
                # 현재 사용자가 이 사용자를 팔로우하는지 확인 (자기 자신인 경우 제외)
                is_following = False
                if current_user_id and current_user_id != user_id_val:
                    is_following = await self._is_following(current_user_id, user_id_val)
                elif current_user_id == user_id_val:
                    is_following = True  # 자기 자신

                following.append(
                    FollowUser(
                        user_id=user_id_val,
                        name=name,
                        profile_image_url=profile_image_url,
                        is_following=is_following,
                        created_at=created_at,
                    )
                )

            # 총 팔로잉 수
            total_stmt = select(func.count(UserFollowModel.following_id)).where(
                UserFollowModel.follower_id == user_id
            )
            total_result = self.db.execute(total_stmt)
            total = total_result.scalar() or 0

            return FollowListResponse(users=following, total=total)

        except Exception as e:
            raise Exception(f"팔로잉 목록 조회 실패: {str(e)}")

    async def is_following(self, follower_id: int, following_id: int) -> bool:
        """팔로우 관계 확인"""
        return await self._is_following(follower_id, following_id)

    async def _is_following(self, follower_id: int, following_id: int) -> bool:
        """내부 팔로우 관계 확인 메서드"""
        try:
            stmt = select(UserFollowModel).where(
                and_(
                    UserFollowModel.follower_id == follower_id,
                    UserFollowModel.following_id == following_id,
                )
            )
            result = self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        except Exception:
            return False

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()
