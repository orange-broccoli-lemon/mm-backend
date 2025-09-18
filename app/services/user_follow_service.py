# app/services/user_follow_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from app.models.user_follow import UserFollowModel
from app.models.user import UserModel
from app.schemas.user_follow import UserFollow, FollowStats, FollowUser, FollowListResponse
from app.database import SessionLocal


class UserFollowService:

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        """데이터베이스 세션 생성"""
        return SessionLocal()

    async def follow_user(self, follower_id: int, following_id: int) -> UserFollow:
        """사용자 팔로우"""
        db = self._get_db()
        try:
            # 자기 자신 팔로우 방지
            if follower_id == following_id:
                raise Exception("자기 자신을 팔로우할 수 없습니다")

            # 팔로우할 사용자 존재 확인
            if not self._user_exists(following_id, db):
                raise Exception("팔로우할 사용자를 찾을 수 없습니다")

            # 이미 팔로우 중인지 확인
            if self._is_following_with_db(follower_id, following_id, db):
                raise Exception("이미 팔로우 중인 사용자입니다")

            # 새 팔로우 관계 생성
            new_follow = UserFollowModel(follower_id=follower_id, following_id=following_id)

            db.add(new_follow)
            db.commit()
            db.refresh(new_follow)

            return UserFollow(
                follower_id=new_follow.follower_id,
                following_id=new_follow.following_id,
                created_at=new_follow.created_at,
            )

        except Exception as e:
            db.rollback()
            raise Exception(f"팔로우 실패: {str(e)}")
        finally:
            db.close()

    async def unfollow_user(self, follower_id: int, following_id: int) -> bool:
        """사용자 언팔로우"""
        db = self._get_db()
        try:
            follow_stmt = select(UserFollowModel).where(
                and_(
                    UserFollowModel.follower_id == follower_id,
                    UserFollowModel.following_id == following_id,
                )
            )
            follow_result = db.execute(follow_stmt)
            follow = follow_result.scalar_one_or_none()

            if not follow:
                raise Exception("팔로우 관계를 찾을 수 없습니다")

            db.delete(follow)
            db.commit()

            return True

        except Exception as e:
            db.rollback()
            raise Exception(f"언팔로우 실패: {str(e)}")
        finally:
            db.close()

    async def get_follow_stats(self, user_id: int) -> FollowStats:
        """사용자의 팔로우 통계"""
        db = self._get_db()
        try:
            # 팔로워 수와 팔로잉 수를 한 번에 조회
            followers_count = self._get_followers_count_with_db(user_id, db)
            following_count = self._get_following_count_with_db(user_id, db)

            return FollowStats(
                user_id=user_id, followers_count=followers_count, following_count=following_count
            )

        except Exception as e:
            raise Exception(f"팔로우 통계 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_followers(
        self, user_id: int, current_user_id: Optional[int] = None, skip: int = 0, limit: int = 20
    ) -> FollowListResponse:
        """팔로워 목록 조회"""
        db = self._get_db()
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

            result = db.execute(stmt)
            followers_data = result.all()

            # 현재 사용자가 팔로우하는 사용자들의 ID 일괄 조회
            follower_ids = [row[0] for row in followers_data]
            following_ids_set = set()

            if current_user_id and follower_ids:
                following_ids_set = self._get_following_ids_set(current_user_id, follower_ids, db)

            followers = []
            for user_id_val, name, profile_image_url, created_at in followers_data:
                is_following = user_id_val in following_ids_set

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
            total = self._get_followers_count_with_db(user_id, db)

            return FollowListResponse(users=followers, total=total)

        except Exception as e:
            raise Exception(f"팔로워 목록 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_following(
        self, user_id: int, current_user_id: Optional[int] = None, skip: int = 0, limit: int = 20
    ) -> FollowListResponse:
        """팔로잉 목록 조회"""
        db = self._get_db()
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

            result = db.execute(stmt)
            following_data = result.all()

            # 현재 사용자가 팔로우하는 사용자들의 ID 일괄 조회
            following_user_ids = [row[0] for row in following_data]
            following_ids_set = set()

            if current_user_id and following_user_ids:
                following_ids_set = self._get_following_ids_set(
                    current_user_id, following_user_ids, db
                )

            following = []
            for user_id_val, name, profile_image_url, created_at in following_data:
                # 현재 사용자가 이 사용자를 팔로우하는지 확인 (자기 자신인 경우 제외)
                is_following = False
                if current_user_id and current_user_id != user_id_val:
                    is_following = user_id_val in following_ids_set
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
            total = self._get_following_count_with_db(user_id, db)

            return FollowListResponse(users=following, total=total)

        except Exception as e:
            raise Exception(f"팔로잉 목록 조회 실패: {str(e)}")
        finally:
            db.close()

    async def is_following(self, follower_id: int, following_id: int) -> bool:
        """팔로우 관계 확인"""
        db = self._get_db()
        try:
            return self._is_following_with_db(follower_id, following_id, db)
        finally:
            db.close()

    def _user_exists(self, user_id: int, db: Session) -> bool:
        """사용자 존재 여부 확인"""
        stmt = select(UserModel).where(UserModel.user_id == user_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _is_following_with_db(self, follower_id: int, following_id: int, db: Session) -> bool:
        """팔로우 관계 확인"""
        try:
            stmt = select(UserFollowModel).where(
                and_(
                    UserFollowModel.follower_id == follower_id,
                    UserFollowModel.following_id == following_id,
                )
            )
            result = db.execute(stmt)
            return result.scalar_one_or_none() is not None

        except Exception:
            return False

    def _get_followers_count_with_db(self, user_id: int, db: Session) -> int:
        """팔로워 수 조회"""
        try:
            stmt = select(func.count(UserFollowModel.follower_id)).where(
                UserFollowModel.following_id == user_id
            )
            result = db.execute(stmt)
            return result.scalar() or 0
        except Exception:
            return 0

    def _get_following_count_with_db(self, user_id: int, db: Session) -> int:
        """팔로잉 수 조회"""
        try:
            stmt = select(func.count(UserFollowModel.following_id)).where(
                UserFollowModel.follower_id == user_id
            )
            result = db.execute(stmt)
            return result.scalar() or 0
        except Exception:
            return 0

    def _get_following_ids_set(
        self, current_user_id: int, target_user_ids: List[int], db: Session
    ) -> set:
        """현재 사용자가 팔로우하는 대상 사용자들의 ID 집합"""
        try:
            stmt = select(UserFollowModel.following_id).where(
                and_(
                    UserFollowModel.follower_id == current_user_id,
                    UserFollowModel.following_id.in_(target_user_ids),
                )
            )
            result = db.execute(stmt).fetchall()
            return {row[0] for row in result}
        except Exception:
            return set()

    async def _is_following(self, follower_id: int, following_id: int) -> bool:
        """내부 팔로우 관계 확인 메서드"""
        return await self.is_following(follower_id, following_id)
