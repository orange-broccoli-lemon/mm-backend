# app/services/user_service.py

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.user import UserModel
from app.models.user_follow import UserFollowModel
from app.models.person_follow import PersonFollowModel
from app.models.comment import CommentModel
from app.models.comment_like import CommentLikeModel
from app.schemas.user import (
    User, UserDetail, UserCreateEmail, UserCreateGoogle, 
    UserLoginEmail, UserLoginGoogle, UserComment, 
    UserFollower, UserFollowing, UserFollowingPerson
)
from app.database import get_db
from app.core.auth import get_password_hash, verify_password


class UserService:

    def __init__(self):
        self.db: Session = next(get_db())

    async def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()

            if user_model:
                return User.from_orm(user_model)
            return None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")

    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.google_id == google_id)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()

            if user_model:
                return User.from_orm(user_model)
            return None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")

    async def create_user_email(self, user_data: UserCreateEmail) -> User:
        try:
            # 이메일 중복 체크
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise Exception("이미 등록된 이메일입니다")

            # 비밀번호 해시화
            hashed_password = get_password_hash(user_data.password)

            # 사용자 생성 (이메일 방식)
            user_model = UserModel(
                google_id=None,
                email=user_data.email,
                password_hash=hashed_password,
                name=user_data.name,
                profile_image_url=user_data.profile_image_url
            )

            self.db.add(user_model)
            self.db.commit()
            self.db.refresh(user_model)

            return User.from_orm(user_model)

        except Exception as e:
            self.db.rollback()
            raise Exception(f"이메일 회원가입 실패: {str(e)}")

    async def create_user_google(self, user_data: UserCreateGoogle) -> User:
        try:
            # 이메일 중복 체크
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise Exception("이미 등록된 이메일입니다")

            # Google ID 중복 체크
            existing_google_user = await self.get_user_by_google_id(user_data.google_id)
            if existing_google_user:
                raise Exception("이미 등록된 Google 계정입니다")

            # 사용자 생성 (구글 방식)
            user_model = UserModel(
                google_id=user_data.google_id,
                email=user_data.email,
                password_hash=None,  # Google 로그인은 비밀번호 없음
                name=user_data.name,
                profile_image_url=user_data.profile_image_url
            )

            self.db.add(user_model)
            self.db.commit()
            self.db.refresh(user_model)

            return User.from_orm(user_model)

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Google 회원가입 실패: {str(e)}")

    async def authenticate_user_email(self, email: str, password: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()

            if not user_model:
                return None

            # Google 계정인 경우 이메일 로그인 불가
            if user_model.google_id and not user_model.password_hash:
                return None

            # 비밀번호 확인
            if not verify_password(password, user_model.password_hash):
                return None

            # 마지막 로그인 시간 업데이트
            from datetime import datetime
            user_model.last_login = datetime.utcnow()
            self.db.commit()

            return User.from_orm(user_model)

        except Exception as e:
            raise Exception(f"이메일 로그인 실패: {str(e)}")

    async def authenticate_user_google(self, email: str, google_id: str) -> Optional[User]:
        try:
            # Google ID로 사용자 찾기
            user = await self.get_user_by_google_id(google_id)
            if user and user.email == email:
                # 마지막 로그인 시간 업데이트
                stmt = select(UserModel).where(UserModel.google_id == google_id)
                result = self.db.execute(stmt)
                user_model = result.scalar_one_or_none()

                if user_model:
                    from datetime import datetime
                    user_model.last_login = datetime.utcnow()
                    self.db.commit()

                return user
            return None

        except Exception as e:
            raise Exception(f"Google 로그인 실패: {str(e)}")

    async def check_email_exists(self, email: str) -> bool:
        user = await self.get_user_by_email(email)
        return user is not None

    # 상세 페이지용 메서드 추가
    async def get_user_detail(self, user_id: int, current_user: Optional[User] = None) -> Optional[UserDetail]:
        """사용자 상세 정보 조회"""
        try:
            # 기본 사용자 정보 조회
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()

            if not user_model:
                return None

            # 본인의 정보인지 확인
            is_own_profile = current_user and current_user.user_id == user_id

            # 기본 사용자 정보 구성
            user_data = {
                "user_id": user_model.user_id,
                "name": user_model.name,
                "profile_image_url": user_model.profile_image_url,
                "created_at": user_model.created_at,
                "is_active": user_model.is_active,
            }

            # 본인만 볼 수 있는 정보 추가
            if is_own_profile:
                user_data.update({
                    "email": user_model.email,
                    "last_login": user_model.last_login,
                })

            # 모든 관련 데이터를 병렬로 조회
            import asyncio

            tasks = [
                self._get_followers_count(user_id),
                self._get_following_count(user_id),
                self._get_following_persons_count(user_id),
                self._get_comments_count(user_id),
                self.get_user_followers(user_id, limit=10, offset=0),
                self.get_user_following(user_id, limit=10, offset=0),
                self.get_user_following_persons(user_id, limit=10, offset=0),
                self.get_user_comments(user_id, limit=10, offset=0)
            ]

            # 모든 쿼리를 병렬로 실행
            (
                followers_count,
                following_count,
                following_persons_count,
                comments_count,
                followers_list,
                following_list,
                following_persons_list,
                comments_list
            ) = await asyncio.gather(*tasks)

            # 통합 데이터 구성
            user_data.update({
                "followers_count": followers_count,
                "following_count": following_count,
                "following_persons_count": following_persons_count,
                "comments_count": comments_count,
                "followers": followers_list,
                "following": following_list,
                "following_persons": following_persons_list,
                "recent_comments": comments_list
            })

            return UserDetail(**user_data)

        except Exception as e:
            raise Exception(f"사용자 상세 정보 조회 실패: {str(e)}")

    async def _get_followers_count(self, user_id: int) -> int:
        """팔로워 수 조회"""
        try:
            stmt = select(func.count(UserFollowModel.follower_id)).where(
                UserFollowModel.following_id == user_id
            )
            result = self.db.execute(stmt)
            return result.scalar() or 0
        except:
            return 0

    async def _get_following_count(self, user_id: int) -> int:
        """팔로잉 수 조회"""
        try:
            stmt = select(func.count(UserFollowModel.following_id)).where(
                UserFollowModel.follower_id == user_id
            )
            result = self.db.execute(stmt)
            return result.scalar() or 0
        except:
            return 0

    async def _get_following_persons_count(self, user_id: int) -> int:
        """팔로우 중인 인물 수 조회"""
        try:
            stmt = select(func.count(PersonFollowModel.person_id)).where(
                PersonFollowModel.user_id == user_id
            )
            result = self.db.execute(stmt)
            return result.scalar() or 0
        except:
            return 0

    async def _get_comments_count(self, user_id: int) -> int:
        """작성한 코멘트 수 조회"""
        try:
            stmt = select(func.count(CommentModel.comment_id)).where(
                CommentModel.user_id == user_id
            )
            result = self.db.execute(stmt)
            return result.scalar() or 0
        except:
            return 0

    async def get_user_followers(self, user_id: int, limit: int = 20, offset: int = 0) -> list[UserFollower]:
        """사용자의 팔로워 목록 조회"""
        try:
            stmt = select(
                UserModel.user_id,
                UserModel.name,
                UserModel.profile_image_url,
                UserFollowModel.created_at
            ).join(
                UserFollowModel, UserModel.user_id == UserFollowModel.follower_id
            ).where(
                UserFollowModel.following_id == user_id
            ).order_by(
                UserFollowModel.created_at.desc()
            ).limit(limit).offset(offset)

            result = self.db.execute(stmt)
            followers = []

            for row in result:
                followers.append(UserFollower(
                    user_id=row.user_id,
                    name=row.name,
                    profile_image_url=row.profile_image_url,
                    created_at=row.created_at
                ))

            return followers

        except Exception as e:
            return []

    async def get_user_following(self, user_id: int, limit: int = 20, offset: int = 0) -> list[UserFollowing]:
        """사용자의 팔로잉 목록 조회"""
        try:
            stmt = select(
                UserModel.user_id,
                UserModel.name,
                UserModel.profile_image_url,
                UserFollowModel.created_at
            ).join(
                UserFollowModel, UserModel.user_id == UserFollowModel.following_id
            ).where(
                UserFollowModel.follower_id == user_id
            ).order_by(
                UserFollowModel.created_at.desc()
            ).limit(limit).offset(offset)

            result = self.db.execute(stmt)
            following = []

            for row in result:
                following.append(UserFollowing(
                    user_id=row.user_id,
                    name=row.name,
                    profile_image_url=row.profile_image_url,
                    created_at=row.created_at
                ))

            return following

        except Exception as e:
            return []

    async def get_user_following_persons(self, user_id: int, limit: int = 20, offset: int = 0) -> list[UserFollowingPerson]:
        """사용자가 팔로우 중인 인물 목록 조회"""
        try:
            from app.models.person import PersonModel

            stmt = select(
                PersonModel.person_id,
                PersonModel.name,
                PersonModel.profile_image_url,
                PersonFollowModel.created_at
            ).join(
                PersonFollowModel, PersonModel.person_id == PersonFollowModel.person_id
            ).where(
                PersonFollowModel.user_id == user_id
            ).order_by(
                PersonFollowModel.created_at.desc()
            ).limit(limit).offset(offset)

            result = self.db.execute(stmt)
            following_persons = []

            for row in result:
                following_persons.append(UserFollowingPerson(
                    person_id=row.person_id,
                    name=row.name,
                    profile_image_url=row.profile_image_url,
                    created_at=row.created_at
                ))

            return following_persons

        except Exception as e:
            return []

    async def get_user_comments(self, user_id: int, limit: int = 20, offset: int = 0) -> list[UserComment]:
        """사용자의 코멘트 목록 조회 (좋아요 수 포함)"""
        try:
            # 코멘트와 좋아요 수를 함께 조회
            stmt = select(
                CommentModel.comment_id,
                CommentModel.movie_id,
                CommentModel.content,
                CommentModel.is_spoiler,
                CommentModel.created_at,
                func.count(CommentLikeModel.comment_id).label('likes_count')
            ).outerjoin(
                CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id
            ).where(
                CommentModel.user_id == user_id
            ).group_by(
                CommentModel.comment_id,
                CommentModel.movie_id,
                CommentModel.content,
                CommentModel.is_spoiler,
                CommentModel.created_at
            ).order_by(
                CommentModel.created_at.desc()
            ).limit(limit).offset(offset)

            result = self.db.execute(stmt)
            comments = []

            for row in result:
                comments.append(UserComment(
                    comment_id=row.comment_id,
                    movie_id=row.movie_id,
                    content=row.content,
                    is_spoiler=row.is_spoiler,
                    likes_count=row.likes_count,
                    created_at=row.created_at
                ))

            return comments

        except Exception as e:
            return []

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
