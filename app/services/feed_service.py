# app/services/feed_service.py

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc
from app.models.comment import CommentModel
from app.models.comment_like import CommentLikeModel
from app.models.user_follow import UserFollowModel
from app.models.user import UserModel
from app.models.movie import MovieModel
from app.schemas.feed import FeedComment, FeedResponse, FeedFilter
from app.database import get_db


class FeedService:

    def __init__(self):
        self.db: Session = next(get_db())

    async def get_user_feed(
        self, user_id: int, skip: int = 0, limit: int = 20, feed_filter: Optional[FeedFilter] = None
    ) -> FeedResponse:
        """사용자의 피드 조회"""
        try:
            # 기본 필터 설정
            if feed_filter is None:
                feed_filter = FeedFilter()

            # 팔로우한 유저들의 ID 조회
            following_stmt = select(UserFollowModel.following_id).where(
                UserFollowModel.follower_id == user_id
            )
            following_result = self.db.execute(following_stmt)
            following_ids = [row[0] for row in following_result.fetchall()]

            if not following_ids:
                # 팔로우한 사람이 없으면 빈 피드 반환
                return FeedResponse(comments=[], total=0, has_next=False)

            # 기본 쿼리 구성
            base_query = (
                select(
                    CommentModel.comment_id,
                    CommentModel.movie_id,
                    CommentModel.content,
                    CommentModel.is_spoiler,
                    CommentModel.spoiler_confidence,
                    CommentModel.created_at,
                    CommentModel.user_id.label("author_id"),
                    UserModel.name.label("author_name"),
                    UserModel.profile_image_url.label("author_profile_image"),
                    MovieModel.title.label("movie_title"),
                    MovieModel.poster_url.label("movie_poster_url"),
                    MovieModel.release_date.label("movie_release_date"),
                    func.count(CommentLikeModel.comment_id).label("likes_count"),
                )
                .select_from(CommentModel)
                .join(UserModel, CommentModel.user_id == UserModel.user_id)
                .join(MovieModel, CommentModel.movie_id == MovieModel.movie_id)
                .outerjoin(CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id)
                .where(CommentModel.user_id.in_(following_ids))
                .group_by(
                    CommentModel.comment_id,
                    CommentModel.movie_id,
                    CommentModel.content,
                    CommentModel.is_spoiler,
                    CommentModel.spoiler_confidence,
                    CommentModel.created_at,
                    CommentModel.user_id,
                    UserModel.name,
                    UserModel.profile_image_url,
                    MovieModel.title,
                    MovieModel.poster_url,
                    MovieModel.release_date,
                )
            )

            # 필터 적용
            if not feed_filter.include_spoilers:
                base_query = base_query.where(CommentModel.is_spoiler == False)

            if feed_filter.movie_ids:
                base_query = base_query.where(CommentModel.movie_id.in_(feed_filter.movie_ids))

            if feed_filter.days_ago:
                date_threshold = datetime.utcnow() - timedelta(days=feed_filter.days_ago)
                base_query = base_query.where(CommentModel.created_at >= date_threshold)

            # 정렬 및 페이징
            query = base_query.order_by(desc(CommentModel.created_at)).offset(skip).limit(limit + 1)

            result = self.db.execute(query)
            rows = result.fetchall()

            # 다음 페이지 존재 여부 확인
            has_next = len(rows) > limit
            if has_next:
                rows = rows[:-1]  # 마지막 항목 제거

            # FeedComment 객체 생성
            feed_comments = []
            for row in rows:
                # 현재 사용자가 이 댓글을 좋아요했는지 확인
                is_liked = await self._is_comment_liked_by_user(row.comment_id, user_id)

                feed_comment = FeedComment(
                    comment_id=row.comment_id,
                    movie_id=row.movie_id,
                    content=row.content,
                    is_spoiler=row.is_spoiler,
                    spoiler_confidence=row.spoiler_confidence,
                    likes_count=row.likes_count or 0,
                    is_liked=is_liked,
                    created_at=row.created_at,
                    author_id=row.author_id,
                    author_name=row.author_name,
                    author_profile_image=row.author_profile_image,
                    movie_title=row.movie_title,
                    movie_poster_url=row.movie_poster_url,
                    movie_release_date=(
                        str(row.movie_release_date) if row.movie_release_date else None
                    ),
                )
                feed_comments.append(feed_comment)

            # 총 댓글 수 계산 (페이징용)
            total_query = select(func.count(CommentModel.comment_id)).where(
                CommentModel.user_id.in_(following_ids)
            )

            # 총 개수에도 같은 필터 적용
            if not feed_filter.include_spoilers:
                total_query = total_query.where(CommentModel.is_spoiler == False)
            if feed_filter.movie_ids:
                total_query = total_query.where(CommentModel.movie_id.in_(feed_filter.movie_ids))
            if feed_filter.days_ago:
                date_threshold = datetime.utcnow() - timedelta(days=feed_filter.days_ago)
                total_query = total_query.where(CommentModel.created_at >= date_threshold)

            total_result = self.db.execute(total_query)
            total = total_result.scalar() or 0

            return FeedResponse(comments=feed_comments, total=total, has_next=has_next)

        except Exception as e:
            raise Exception(f"피드 조회 실패: {str(e)}")

    async def get_trending_feed(
        self, user_id: int, skip: int = 0, limit: int = 20, hours_ago: int = 24
    ) -> FeedResponse:
        """인기 댓글 피드 (좋아요가 많은 순)"""
        try:
            # 시간 임계값 설정
            time_threshold = datetime.utcnow() - timedelta(hours=hours_ago)

            # 인기 댓글 쿼리 (좋아요 많은 순)
            query = (
                select(
                    CommentModel.comment_id,
                    CommentModel.movie_id,
                    CommentModel.content,
                    CommentModel.is_spoiler,
                    CommentModel.spoiler_confidence,
                    CommentModel.created_at,
                    CommentModel.user_id.label("author_id"),
                    UserModel.name.label("author_name"),
                    UserModel.profile_image_url.label("author_profile_image"),
                    MovieModel.title.label("movie_title"),
                    MovieModel.poster_url.label("movie_poster_url"),
                    MovieModel.release_date.label("movie_release_date"),
                    func.count(CommentLikeModel.comment_id).label("likes_count"),
                )
                .select_from(CommentModel)
                .join(UserModel, CommentModel.user_id == UserModel.user_id)
                .join(MovieModel, CommentModel.movie_id == MovieModel.movie_id)
                .outerjoin(CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id)
                .where(CommentModel.created_at >= time_threshold)
                .group_by(
                    CommentModel.comment_id,
                    CommentModel.movie_id,
                    CommentModel.content,
                    CommentModel.is_spoiler,
                    CommentModel.spoiler_confidence,
                    CommentModel.created_at,
                    CommentModel.user_id,
                    UserModel.name,
                    UserModel.profile_image_url,
                    MovieModel.title,
                    MovieModel.poster_url,
                    MovieModel.release_date,
                )
                .order_by(
                    desc(func.count(CommentLikeModel.comment_id)), desc(CommentModel.created_at)
                )
                .offset(skip)
                .limit(limit + 1)
            )

            result = self.db.execute(query)
            rows = result.fetchall()

            # 다음 페이지 존재 여부 확인
            has_next = len(rows) > limit
            if has_next:
                rows = rows[:-1]

            # FeedComment 객체 생성
            feed_comments = []
            for row in rows:
                is_liked = await self._is_comment_liked_by_user(row.comment_id, user_id)

                feed_comment = FeedComment(
                    comment_id=row.comment_id,
                    movie_id=row.movie_id,
                    content=row.content,
                    is_spoiler=row.is_spoiler,
                    spoiler_confidence=row.spoiler_confidence,
                    likes_count=row.likes_count or 0,
                    is_liked=is_liked,
                    created_at=row.created_at,
                    author_id=row.author_id,
                    author_name=row.author_name,
                    author_profile_image=row.author_profile_image,
                    movie_title=row.movie_title,
                    movie_poster_url=row.movie_poster_url,
                    movie_release_date=(
                        str(row.movie_release_date) if row.movie_release_date else None
                    ),
                )
                feed_comments.append(feed_comment)

            # 총 개수
            total_query = select(func.count(CommentModel.comment_id)).where(
                CommentModel.created_at >= time_threshold
            )
            total_result = self.db.execute(total_query)
            total = total_result.scalar() or 0

            return FeedResponse(comments=feed_comments, total=total, has_next=has_next)

        except Exception as e:
            raise Exception(f"트렌딩 피드 조회 실패: {str(e)}")

    async def _is_comment_liked_by_user(self, comment_id: int, user_id: int) -> bool:
        """사용자가 댓글을 좋아요했는지 확인"""
        try:
            stmt = select(CommentLikeModel).where(
                and_(CommentLikeModel.comment_id == comment_id, CommentLikeModel.user_id == user_id)
            )
            result = self.db.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception:
            return False

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()
