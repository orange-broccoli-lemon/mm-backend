# app/services/user_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case, and_
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
    UserFollowingPerson,
)
from app.schemas.comment import CommentWithMovie
from app.schemas.search import UserSearchResult
from app.database import SessionLocal
from app.core.auth import get_password_hash, verify_password
from fastapi import UploadFile
import uuid
from pathlib import Path


class UserService:

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        """데이터베이스 세션 생성"""
        return SessionLocal()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        db = self._get_db()
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            result = db.execute(stmt)
            user_model = result.scalar_one_or_none()

            return User.from_orm(user_model) if user_model else None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        db = self._get_db()
        try:
            stmt = select(UserModel).where(UserModel.google_id == google_id)
            result = db.execute(stmt)
            user_model = result.scalar_one_or_none()

            return User.from_orm(user_model) if user_model else None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 기본 정보 조회"""
        db = self._get_db()
        try:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            result = db.execute(stmt)
            user_model = result.scalar_one_or_none()

            return User.from_orm(user_model) if user_model else None

        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")
        finally:
            db.close()

    async def create_user_email(self, user_data: UserCreateEmail) -> User:
        db = self._get_db()
        try:
            # 이메일 중복 체크
            if await self._check_user_by_email(user_data.email, db):
                raise Exception("이미 등록된 이메일입니다")

            # 사용자 생성
            user_model = UserModel(
                google_id=None,
                email=user_data.email,
                password_hash=get_password_hash(user_data.password),
                name=user_data.name,
                profile_image_url=user_data.profile_image_url,
            )

            db.add(user_model)
            db.commit()
            db.refresh(user_model)

            return User.from_orm(user_model)

        except Exception as e:
            db.rollback()
            raise Exception(f"이메일 회원가입 실패: {str(e)}")
        finally:
            db.close()

    async def create_user_google(self, user_data: UserCreateGoogle) -> User:
        db = self._get_db()
        try:
            # 중복 체크
            if await self._check_user_by_email(user_data.email, db):
                raise Exception("이미 등록된 이메일입니다")

            if await self._check_user_by_google_id(user_data.google_id, db):
                raise Exception("이미 등록된 Google 계정입니다")

            # 사용자 생성
            user_model = UserModel(
                google_id=user_data.google_id,
                email=user_data.email,
                password_hash=None,
                name=user_data.name,
                profile_image_url=user_data.profile_image_url,
            )

            db.add(user_model)
            db.commit()
            db.refresh(user_model)

            return User.from_orm(user_model)

        except Exception as e:
            db.rollback()
            raise Exception(f"Google 회원가입 실패: {str(e)}")
        finally:
            db.close()

    async def authenticate_user_email(self, email: str, password: str) -> Optional[User]:
        db = self._get_db()
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            user_model = db.execute(stmt).scalar_one_or_none()

            if (
                not user_model
                or user_model.google_id
                or not verify_password(password, user_model.password_hash)
            ):
                return None

            # 마지막 로그인 시간 업데이트
            from datetime import datetime

            user_model.last_login = datetime.utcnow()
            db.commit()

            return User.from_orm(user_model)

        except Exception as e:
            raise Exception(f"이메일 로그인 실패: {str(e)}")
        finally:
            db.close()

    async def authenticate_user_google(self, email: str, google_id: str) -> Optional[User]:
        db = self._get_db()
        try:
            # Google ID로 사용자 조회
            stmt = select(UserModel).where(UserModel.google_id == google_id)
            user_model = db.execute(stmt).scalar_one_or_none()

            if user_model and user_model.email == email:
                # 마지막 로그인 시간 업데이트
                from datetime import datetime

                user_model.last_login = datetime.utcnow()
                db.commit()

                return User.from_orm(user_model)

            return None

        except Exception as e:
            raise Exception(f"Google 로그인 실패: {str(e)}")
        finally:
            db.close()

    async def check_email_exists(self, email: str) -> bool:
        user = await self.get_user_by_email(email)
        return user is not None

    async def get_user_detail(
        self, user_id: int, current_user: Optional[User] = None
    ) -> Optional[UserDetail]:
        """사용자 상세 정보 조회"""
        db = self._get_db()
        try:
            # 1. 기본 사용자 정보 조회
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_model = db.execute(stmt).scalar_one_or_none()

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
                "profile_review": user_model.profile_review,
                "profile_review_date": user_model.profile_review_date,
            }

            # 본인만 볼 수 있는 정보
            if is_own_profile:
                user_data.update(
                    {
                        "email": user_model.email,
                        "last_login": user_model.last_login,
                    }
                )

            # 4. 통계 정보 조회
            counts = await self._get_counts_with_db(user_id, db)
            user_data.update(counts)

            return UserDetail(**user_data)

        except Exception as e:
            raise Exception(f"사용자 상세 정보 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_user_comments_with_movies(
        self, user_id: int, limit: int = 20, offset: int = 0, include_private: bool = False
    ) -> list[CommentWithMovie]:
        """사용자 댓글 목록 조회"""
        db = self._get_db()
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

            result = db.execute(stmt)
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
        finally:
            db.close()

    async def update_user_profile_review(self, user_id: int, profile_review: str) -> bool:
        """사용자 프로필 분석 결과 업데이트"""
        db = self._get_db()
        try:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_model = db.execute(stmt).scalar_one_or_none()

            if not user_model:
                return False

            from datetime import datetime

            user_model.profile_review = profile_review
            user_model.profile_review_date = datetime.utcnow()

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()

    async def get_all_users(self) -> list[User]:
        """DB 전체 사용자 조회"""
        db = self._get_db()
        try:
            stmt = select(UserModel)
            result = db.execute(stmt)
            return [User.from_orm(user_model) for user_model in result.scalars()]

        except Exception as e:
            raise Exception(f"전체 사용자 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_following_persons_list(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> List[UserFollowingPerson]:
        """팔로우 중인 인물 목록"""
        db = self._get_db()
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
                .offset(offset)
            )

            result = db.execute(stmt)
            return [
                UserFollowingPerson(
                    person_id=row.person_id,
                    name=row.name,
                    profile_image_url=row.profile_image_url,
                    created_at=row.created_at,
                )
                for row in result
            ]

        except Exception as e:
            return []
        finally:
            db.close()

    async def get_following_persons_count(self, user_id: int) -> int:
        """팔로우 중인 인물 총 개수"""
        db = self._get_db()
        try:
            stmt = select(func.count(PersonFollowModel.person_id)).where(
                PersonFollowModel.user_id == user_id
            )
            return db.execute(stmt).scalar() or 0
        except Exception:
            return 0
        finally:
            db.close()

    async def search_users_by_name(self, name: str) -> List[UserSearchResult]:
        db = self._get_db()
        try:
            stmt = (
                select(UserModel)
                .where(UserModel.name.ilike(f"%{name}%"))
                .order_by(case((UserModel.name.ilike(f"{name}%"), 0), else_=1), UserModel.name)
            )
            result = db.execute(stmt)
            return [UserSearchResult.from_orm(user_model) for user_model in result.scalars().all()]
        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_users_with_comments(self, min_comments: int = 5) -> List[dict]:
        """댓글이 있는 사용자 목록 조회 (프로필 분석용)"""
        db = self._get_db()
        try:
            stmt = (
                select(
                    UserModel.user_id,
                    UserModel.name,
                    func.count(CommentModel.comment_id).label("comments_count"),
                )
                .join(CommentModel, UserModel.user_id == CommentModel.user_id)
                .where(and_(UserModel.is_active == True, CommentModel.is_public == True))
                .group_by(UserModel.user_id, UserModel.name)
                .having(func.count(CommentModel.comment_id) >= min_comments)
                .order_by(func.count(CommentModel.comment_id).desc())
            )

            result = db.execute(stmt)
            return [
                {"user_id": row.user_id, "name": row.name, "comments_count": row.comments_count}
                for row in result
            ]

        except Exception as e:
            return []
        finally:
            db.close()

    async def update_user_profile(
        self, user_id: int, update_data: dict, profile_image_url: Optional[UploadFile] = None
    ) -> tuple[User, List[str]]:
        """사용자 프로필 업데이트"""
        db = self._get_db()
        try:
            # 사용자 조회
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_model = db.execute(stmt).scalar_one_or_none()

            if not user_model:
                raise Exception("사용자를 찾을 수 없습니다")

            # Google 계정인 경우 비밀번호 변경 제한
            if user_model.google_id and "password" in update_data:
                raise Exception("Google 계정은 비밀번호를 변경할 수 없습니다")

            updated_fields = []

            # 이름 업데이트
            if "name" in update_data and update_data["name"]:
                user_model.name = update_data["name"]
                updated_fields.append("name")

            # 비밀번호 업데이트
            if "password" in update_data and update_data["password"]:
                user_model.password_hash = get_password_hash(update_data["password"])
                updated_fields.append("password")

            # 프로필 이미지 업데이트
            if profile_image_url:
                image_url = await self._save_profile_image(user_id, profile_image_url)
                user_model.profile_image_url = image_url
                updated_fields.append("profile_image_url")

            if not updated_fields:
                raise Exception("수정할 정보가 없습니다")

            # 업데이트 시간 갱신
            from datetime import datetime

            user_model.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(user_model)

            return User.from_orm(user_model), updated_fields

        except Exception as e:
            db.rollback()
            raise Exception(f"프로필 업데이트 실패: {str(e)}")
        finally:
            db.close()

    async def verify_current_password(self, user_id: int, password: str) -> bool:
        """현재 비밀번호 확인"""
        db = self._get_db()
        try:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_model = db.execute(stmt).scalar_one_or_none()

            if not user_model or user_model.google_id:
                return False

            return verify_password(password, user_model.password_hash)

        except Exception:
            return False
        finally:
            db.close()

    async def _check_user_by_email(self, email: str, db: Session) -> bool:
        """이메일 중복 체크"""
        stmt = select(UserModel).where(UserModel.email == email)
        result = db.execute(stmt).scalar_one_or_none()
        return result is not None

    async def _check_user_by_google_id(self, google_id: str, db: Session) -> bool:
        """Google ID 중복 체크"""
        stmt = select(UserModel).where(UserModel.google_id == google_id)
        result = db.execute(stmt).scalar_one_or_none()
        return result is not None

    async def _get_counts_with_db(self, user_id: int, db: Session) -> dict:
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

            result = db.execute(stmt)
            stats = result.first()

            return {
                "followers_count": stats.followers_count or 0,
                "following_count": stats.following_count or 0,
                "following_persons_count": stats.following_persons_count or 0,
                "comments_count": stats.comments_count or 0,
                "liked_movies_count": stats.liked_movies_count or 0,
                "watchlist_count": stats.watchlist_count or 0,
            }

        except Exception:
            return {
                "followers_count": 0,
                "following_count": 0,
                "following_persons_count": 0,
                "comments_count": 0,
                "liked_movies_count": 0,
                "watchlist_count": 0,
            }

    async def _save_profile_image(self, user_id: int, image_file: UploadFile) -> str:
        """프로필 이미지 파일 저장"""
        try:
            # 파일 유효성 검사
            if not image_file.content_type or not image_file.content_type.startswith("image/"):
                raise Exception("이미지 파일만 업로드 가능합니다")

            # 파일 크기 제한 (5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            content = await image_file.read()
            if len(content) > max_size:
                raise Exception("파일 크기는 5MB를 초과할 수 없습니다")

            # 저장 디렉토리 생성
            upload_dir = Path("static/profile_images")
            upload_dir.mkdir(parents=True, exist_ok=True)

            # 고유한 파일명 생성
            file_extension = (
                image_file.filename.split(".")[-1] if "." in image_file.filename else "jpg"
            )
            unique_filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
            file_path = upload_dir / unique_filename

            # 파일 저장
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            # URL 반환
            return f"/static/profile_images/{unique_filename}"

        except Exception as e:
            raise Exception(f"이미지 저장 실패: {str(e)}")
