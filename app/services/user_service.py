# app/services/user_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from app.models.user import UserModel
from app.models.user_follow import UserFollowModel
from app.models.person_follow import PersonFollowModel
from app.models.comment import CommentModel
from app.models.comment_like import CommentLikeModel
from app.models.movie_like import MovieLikeModel
from app.models.watchlist import WatchlistModel
from app.models.movie import MovieModel
from app.models.person import PersonModel
from app.schemas.user import (
    User,
    UserDetail,
    UserCreateEmail,
    UserCreateGoogle,
    UserLoginEmail,
    UserLoginGoogle,
    UserComment,
    UserFollower,
    UserFollowing,
    UserFollowingPerson,
)
from app.schemas.movie import WatchlistMovie
from app.schemas.comment import CommentWithMovie
from app.schemas.search import UserSearchResult
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

            return User.from_orm(user_model) if user_model else None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")

    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.google_id == google_id)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()

            return User.from_orm(user_model) if user_model else None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 기본 정보 조회"""
        try:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()

            return User.from_orm(user_model) if user_model else None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")

    async def create_user_email(self, user_data: UserCreateEmail) -> User:
        try:
            # 이메일 중복 체크
            if await self.get_user_by_email(user_data.email):
                raise Exception("이미 등록된 이메일입니다")

            # 사용자 생성
            user_model = UserModel(
                google_id=None,
                email=user_data.email,
                password_hash=get_password_hash(user_data.password),
                name=user_data.name,
                profile_image_url=user_data.profile_image_url,
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
            # 중복 체크
            if await self.get_user_by_email(user_data.email):
                raise Exception("이미 등록된 이메일입니다")

            if await self.get_user_by_google_id(user_data.google_id):
                raise Exception("이미 등록된 Google 계정입니다")

            # 사용자 생성
            user_model = UserModel(
                google_id=user_data.google_id,
                email=user_data.email,
                password_hash=None,
                name=user_data.name,
                profile_image_url=user_data.profile_image_url,
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
            user_model = self.db.execute(stmt).scalar_one_or_none()

            if (
                not user_model
                or user_model.google_id
                or not verify_password(password, user_model.password_hash)
            ):
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
            user = await self.get_user_by_google_id(google_id)
            if user and user.email == email:
                # 마지막 로그인 시간 업데이트
                stmt = select(UserModel).where(UserModel.google_id == google_id)
                user_model = self.db.execute(stmt).scalar_one_or_none()

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

    # 사용자 상세 정보
    async def get_user_detail(
        self, user_id: int, current_user: Optional[User] = None
    ) -> Optional[UserDetail]:
        """사용자 상세 정보 조회 - 통계만 포함"""
        try:
            print(f"사용자 상세 조회: {user_id}")

            # 1. 기본 사용자 정보 조회
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_model = self.db.execute(stmt).scalar_one_or_none()

            if not user_model:
                return None

            # 2. 본인 프로필 여부 확인
            is_own_profile = current_user and current_user.user_id == user_id

            # 3. 기본 정보 구성
            user_data = {
                "user_id": user_model.user_id,
                "name": user_model.name,
                "profile_image_url": user_model.profile_image_url,
                "created_at": user_model.created_at,
                "is_active": user_model.is_active,
            }

            # 본인만 볼 수 있는 정보
            if is_own_profile:
                user_data.update(
                    {
                        "email": user_model.email,
                        "last_login": user_model.last_login,
                    }
                )

            # 4. 통계 정보만 조회
            counts = await self._get_counts(user_id)
            user_data.update(counts)

            return UserDetail(**user_data)

        except Exception as e:
            print(f"사용자 상세 조회 실패: {str(e)}")
            raise Exception(f"사용자 상세 정보 조회 실패: {str(e)}")

    async def get_user_comments_with_movies(
        self, user_id: int, limit: int = 20, offset: int = 0, include_private: bool = False
    ) -> list[CommentWithMovie]:
        """사용자 댓글 목록 조회 (영화 정보 포함)"""
        try:
            stmt = (
                select(
                    CommentModel.comment_id,
                    CommentModel.content,
                    CommentModel.rating,
                    CommentModel.watched_date,
                    CommentModel.is_spoiler,
                    CommentModel.is_public,
                    CommentModel.created_at,
                    CommentModel.movie_id,
                    MovieModel.title.label("movie_title"),
                    MovieModel.poster_url.label("movie_poster_url"),
                    MovieModel.release_date.label("movie_release_date"),
                    func.count(CommentLikeModel.comment_id).label("likes_count"),
                )
                .outerjoin(MovieModel, CommentModel.movie_id == MovieModel.movie_id)
                .outerjoin(CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id)
                .where(CommentModel.user_id == user_id)
            )

            # 본인이 아닌 경우 공개 댓글만 조회
            if not include_private:
                stmt = stmt.where(CommentModel.is_public == True)

            stmt = (
                stmt.group_by(
                    CommentModel.comment_id,
                    CommentModel.content,
                    CommentModel.rating,
                    CommentModel.watched_date,
                    CommentModel.is_spoiler,
                    CommentModel.is_public,
                    CommentModel.created_at,
                    CommentModel.movie_id,
                    MovieModel.title,
                    MovieModel.poster_url,
                    MovieModel.release_date,
                )
                .order_by(CommentModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = self.db.execute(stmt)
            comments = []

            for row in result:
                comments.append(
                    CommentWithMovie(
                        comment_id=row.comment_id,
                        content=row.content,
                        rating=row.rating,
                        watched_date=row.watched_date,
                        is_spoiler=row.is_spoiler,
                        is_public=row.is_public,
                        likes_count=row.likes_count,
                        created_at=row.created_at,
                        movie_id=row.movie_id,
                        movie_title=row.movie_title or f"영화 {row.movie_id}",
                        movie_poster_url=row.movie_poster_url,
                        movie_release_date=row.movie_release_date,
                    )
                )

            return comments

        except Exception as e:
            raise Exception(f"사용자 댓글 조회 실패: {str(e)}")

    async def _get_counts(self, user_id: int) -> dict:
        """모든 통계 정보를 한 번에 조회"""
        try:
            # 서브쿼리들 정의
            followers_subq = (
                select(func.count(UserFollowModel.follower_id))
                .where(UserFollowModel.following_id == user_id)
                .scalar_subquery()
            )

            following_subq = (
                select(func.count(UserFollowModel.following_id))
                .where(UserFollowModel.follower_id == user_id)
                .scalar_subquery()
            )

            following_persons_subq = (
                select(func.count(PersonFollowModel.person_id))
                .where(PersonFollowModel.user_id == user_id)
                .scalar_subquery()
            )

            comments_subq = (
                select(func.count(CommentModel.comment_id))
                .where(CommentModel.user_id == user_id)
                .scalar_subquery()
            )

            liked_movies_subq = (
                select(func.count(MovieLikeModel.movie_id))
                .where(MovieLikeModel.user_id == user_id)
                .scalar_subquery()
            )

            watchlist_subq = (
                select(func.count(WatchlistModel.movie_id))
                .where(WatchlistModel.user_id == user_id)
                .scalar_subquery()
            )

            # 단일 쿼리로 모든 통계 조회
            stmt = select(
                followers_subq.label("followers_count"),
                following_subq.label("following_count"),
                following_persons_subq.label("following_persons_count"),
                comments_subq.label("comments_count"),
                liked_movies_subq.label("liked_movies_count"),
                watchlist_subq.label("watchlist_count"),
            )

            result = self.db.execute(stmt)
            stats = result.first()

            return {
                "followers_count": stats.followers_count or 0,
                "following_count": stats.following_count or 0,
                "following_persons_count": stats.following_persons_count or 0,
                "comments_count": stats.comments_count or 0,
                "liked_movies_count": stats.liked_movies_count or 0,
                "watchlist_count": stats.watchlist_count or 0,
            }

        except Exception as e:
            print(f"통계 조회 실패: {str(e)}")
            return {
                "followers_count": 0,
                "following_count": 0,
                "following_persons_count": 0,
                "comments_count": 0,
                "liked_movies_count": 0,
                "watchlist_count": 0,
            }

    async def _get_followers_list(self, user_id: int, limit: int) -> list[UserFollower]:
        """팔로워 목록"""
        try:
            stmt = (
                select(
                    UserModel.user_id,
                    UserModel.name,
                    UserModel.profile_image_url,
                    UserFollowModel.created_at,
                )
                .join(UserFollowModel, UserModel.user_id == UserFollowModel.follower_id)
                .where(UserFollowModel.following_id == user_id)
                .order_by(UserFollowModel.created_at.desc())
                .limit(limit)
            )

            result = self.db.execute(stmt)
            return [
                UserFollower(
                    user_id=row.user_id,
                    name=row.name,
                    profile_image_url=row.profile_image_url,
                    created_at=row.created_at,
                )
                for row in result
            ]

        except Exception:
            return []

    async def _get_following_list(self, user_id: int, limit: int) -> list[UserFollowing]:
        """팔로잉 목록"""
        try:
            stmt = (
                select(
                    UserModel.user_id,
                    UserModel.name,
                    UserModel.profile_image_url,
                    UserFollowModel.created_at,
                )
                .join(UserFollowModel, UserModel.user_id == UserFollowModel.following_id)
                .where(UserFollowModel.follower_id == user_id)
                .order_by(UserFollowModel.created_at.desc())
                .limit(limit)
            )

            result = self.db.execute(stmt)
            return [
                UserFollowing(
                    user_id=row.user_id,
                    name=row.name,
                    profile_image_url=row.profile_image_url,
                    created_at=row.created_at,
                )
                for row in result
            ]

        except Exception:
            return []

    async def _get_following_persons_list(
        self, user_id: int, limit: int
    ) -> list[UserFollowingPerson]:
        """팔로우 중인 인물 목록"""
        try:
            stmt = (
                select(
                    PersonModel.person_id,
                    PersonModel.name,
                    PersonModel.profile_image_url,
                    PersonFollowModel.created_at,
                )
                .join(PersonFollowModel, PersonModel.person_id == PersonFollowModel.person_id)
                .where(PersonFollowModel.user_id == user_id)
                .order_by(PersonFollowModel.created_at.desc())
                .limit(limit)
            )

            result = self.db.execute(stmt)
            return [
                UserFollowingPerson(
                    person_id=row.person_id,
                    name=row.name,
                    profile_image_url=row.profile_image_url,
                    created_at=row.created_at,
                )
                for row in result
            ]

        except Exception:
            return []

    async def _get_recent_comments(self, user_id: int, limit: int) -> list[UserComment]:
        """최근 코멘트 목록"""
        try:
            stmt = (
                select(
                    CommentModel.comment_id,
                    CommentModel.movie_id,
                    CommentModel.content,
                    CommentModel.is_spoiler,
                    CommentModel.created_at,
                    func.count(CommentLikeModel.comment_id).label("likes_count"),
                )
                .outerjoin(CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id)
                .where(CommentModel.user_id == user_id)
                .group_by(
                    CommentModel.comment_id,
                    CommentModel.movie_id,
                    CommentModel.content,
                    CommentModel.is_spoiler,
                    CommentModel.created_at,
                )
                .order_by(CommentModel.created_at.desc())
                .limit(limit)
            )

            result = self.db.execute(stmt)
            return [
                UserComment(
                    comment_id=row.comment_id,
                    movie_id=row.movie_id,
                    content=row.content,
                    is_spoiler=row.is_spoiler,
                    likes_count=row.likes_count,
                    created_at=row.created_at,
                )
                for row in result
            ]

        except Exception:
            return []

    async def _get_liked_movies(self, user_id: int, limit: int) -> list[WatchlistMovie]:
        """좋아요한 영화 목록"""
        try:
            stmt = (
                select(
                    MovieModel.movie_id,
                    MovieModel.title,
                    MovieModel.poster_url,
                    MovieModel.release_date,
                    MovieModel.average_rating,
                    MovieLikeModel.created_at,
                )
                .join(MovieLikeModel, MovieModel.movie_id == MovieLikeModel.movie_id)
                .where(MovieLikeModel.user_id == user_id)
                .order_by(MovieLikeModel.created_at.desc())
                .limit(limit)
            )

            result = self.db.execute(stmt)
            return [
                WatchlistMovie(
                    movie_id=row.movie_id,
                    title=row.title,
                    poster_url=row.poster_url,
                    release_date=row.release_date,
                    average_rating=row.average_rating,
                    added_at=row.created_at,
                )
                for row in result
            ]

        except Exception:
            return []

    async def _get_watchlist_movies(self, user_id: int, limit: int) -> list[WatchlistMovie]:
        """왓치리스트 영화 목록"""
        try:
            stmt = (
                select(
                    MovieModel.movie_id,
                    MovieModel.title,
                    MovieModel.poster_url,
                    MovieModel.release_date,
                    MovieModel.average_rating,
                    WatchlistModel.created_at,
                )
                .join(WatchlistModel, MovieModel.movie_id == WatchlistModel.movie_id)
                .where(WatchlistModel.user_id == user_id)
                .order_by(WatchlistModel.created_at.desc())
                .limit(limit)
            )

            result = self.db.execute(stmt)
            return [
                WatchlistMovie(
                    movie_id=row.movie_id,
                    title=row.title,
                    poster_url=row.poster_url,
                    release_date=row.release_date,
                    average_rating=row.average_rating,
                    added_at=row.created_at,
                )
                for row in result
            ]

        except Exception:
            return []

    async def get_all_users(self) -> list[User]:
        """개발용 - DB 전체 사용자 조회"""
        try:
            stmt = select(UserModel)
            result = self.db.execute(stmt)
            return [User.from_orm(user_model) for user_model in result.scalars()]

        except Exception as e:
            raise Exception(f"전체 사용자 조회 실패: {str(e)}")
        
    async def search_users_by_name(self, name: str) -> Optional[List[UserSearchResult]]:
        try:
            stmt = (
                select(UserModel)
                .where(UserModel.name.ilike(f"%{name}%"))
                .order_by(
                    case(
                        (UserModel.name.ilike(f"{name}%"), 0),
                        else_=1
                    ),
                    UserModel.name
                )
            )
            result = self.db.execute(stmt)
            return [UserSearchResult.from_orm(user_model) for user_model in result.scalars().all()]
        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")
        

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()
