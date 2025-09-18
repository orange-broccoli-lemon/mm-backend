# app/services/comment_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc
from app.models.comment import CommentModel
from app.models.comment_like import CommentLikeModel
from app.models.user import UserModel
from app.schemas.comment import Comment, CommentCreate, CommentUpdate
from app.database import SessionLocal
from app.ai import check_spoiler_ko, check_emotion_ko, detect_toxicity
from decimal import Decimal


class CommentService:

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        """데이터베이스 세션 생성"""
        return SessionLocal()

    async def get_comment(self, comment_id: int, current_user_id: Optional[int] = None) -> Comment:
        db = self._get_db()
        try:
            stmt = (
                select(
                    CommentModel,
                    UserModel.name.label("user_name"),
                    UserModel.profile_image_url.label("user_profile_image"),
                    func.count(CommentLikeModel.comment_id).label("likes_count"),
                )
                .join(UserModel, CommentModel.user_id == UserModel.user_id)
                .outerjoin(CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id)
                .where(CommentModel.comment_id == comment_id)
                .group_by(CommentModel.comment_id, UserModel.name, UserModel.profile_image_url)
            )
            row = db.execute(stmt).first()
            if not row:
                raise Exception("댓글을 찾을 수 없습니다")
            comment_model, user_name, user_profile_image, likes_count = row
            return self._build_comment_response(
                comment_model, user_name, user_profile_image, likes_count, current_user_id, db
            )
        except Exception as e:
            raise Exception(f"댓글 단건 조회 실패: {str(e)}")
        finally:
            db.close()

    def _run_ai_pipelines(self, content: str) -> dict:
        """AI 파이프라인 실행"""
        try:
            sp = check_spoiler_ko(content)
            is_spoiler = bool(sp.get("is_spoiler", 0))
            spoiler_conf = Decimal(str(sp.get("spoiler_score", 0.0)))
        except Exception:
            is_spoiler, spoiler_conf = False, Decimal("0.0")

        try:
            em = check_emotion_ko(content)
            is_positive = bool(em.get("is_positive", 0))
            positive_conf = Decimal(str(em.get("confidence", 0.0)))
        except Exception:
            is_positive, positive_conf = None, None

        try:
            tx = detect_toxicity(content)
            is_toxic = bool(tx.get("is_toxic", 0))
            toxic_conf = Decimal(str(tx.get("confidence", 0.0)))
        except Exception:
            is_toxic, toxic_conf = None, None

        return {
            "is_spoiler": is_spoiler,
            "spoiler_confidence": spoiler_conf,
            "is_positive": is_positive,
            "positive_confidence": positive_conf,
            "is_toxic": is_toxic,
            "toxic_confidence": toxic_conf,
        }

    async def create_comment(self, comment_data: CommentCreate, user_id: int) -> Comment:
        db = self._get_db()
        try:
            ai = self._run_ai_pipelines(comment_data.content)
            comment_model = CommentModel(
                movie_id=comment_data.movie_id,
                user_id=user_id,
                content=comment_data.content,
                rating=comment_data.rating,
                watched_date=comment_data.watched_date,
                is_spoiler=ai["is_spoiler"],
                spoiler_confidence=ai["spoiler_confidence"],
                is_positive=ai["is_positive"],
                positive_confidence=ai["positive_confidence"],
                is_toxic=ai["is_toxic"],
                toxic_confidence=ai["toxic_confidence"],
                is_public=comment_data.is_public,
            )
            db.add(comment_model)
            db.commit()
            db.refresh(comment_model)

            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_model = db.execute(user_stmt).scalar_one_or_none()

            return self._build_comment_response(
                comment_model,
                user_model.name if user_model else None,
                user_model.profile_image_url if user_model else None,
                likes_count=0,
                current_user_id=None,
                db=db,
                precomputed_is_liked=False,
            )
        except Exception as e:
            db.rollback()
            raise Exception(f"댓글 작성 실패: {str(e)}")
        finally:
            db.close()

    async def update_comment(
        self, comment_id: int, comment_data: CommentUpdate, user_id: int
    ) -> Comment:
        db = self._get_db()
        try:
            stmt = select(CommentModel).where(CommentModel.comment_id == comment_id)
            comment_model = db.execute(stmt).scalar_one_or_none()
            if not comment_model:
                raise Exception("댓글을 찾을 수 없습니다")
            if comment_model.user_id != user_id:
                raise Exception("본인의 댓글만 수정할 수 있습니다")

            content_changed = False
            if comment_data.content is not None and comment_data.content != comment_model.content:
                comment_model.content = comment_data.content
                content_changed = True

            if comment_data.rating is not None:
                comment_model.rating = comment_data.rating
            if comment_data.watched_date is not None:
                comment_model.watched_date = comment_data.watched_date
            if comment_data.is_public is not None:
                comment_model.is_public = comment_data.is_public

            if content_changed:
                ai = self._run_ai_pipelines(comment_model.content)
                comment_model.is_spoiler = ai["is_spoiler"]
                comment_model.spoiler_confidence = ai["spoiler_confidence"]
                comment_model.is_positive = ai["is_positive"]
                comment_model.positive_confidence = ai["positive_confidence"]
                comment_model.is_toxic = ai["is_toxic"]
                comment_model.toxic_confidence = ai["toxic_confidence"]
            else:
                if comment_data.is_spoiler is not None:
                    comment_model.is_spoiler = comment_data.is_spoiler

            db.commit()
            db.refresh(comment_model)

            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_model = db.execute(user_stmt).scalar_one_or_none()
            likes_count = self._get_comment_likes_count_with_db(comment_id, db)

            return self._build_comment_response(
                comment_model,
                user_model.name if user_model else None,
                user_model.profile_image_url if user_model else None,
                likes_count=likes_count,
                current_user_id=user_id,
                db=db,
            )
        except Exception as e:
            db.rollback()
            raise Exception(f"댓글 수정 실패: {str(e)}")
        finally:
            db.close()

    async def get_movie_comments(
        self,
        movie_id: int,
        current_user_id: Optional[int] = None,
        include_spoilers: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Comment]:
        db = self._get_db()
        try:
            stmt = (
                select(CommentModel, UserModel.name, UserModel.profile_image_url)
                .join(UserModel, CommentModel.user_id == UserModel.user_id)
                .where(
                    and_(
                        CommentModel.movie_id == movie_id,
                        CommentModel.is_public == True,
                    )
                )
            )

            if not include_spoilers:
                stmt = stmt.where(CommentModel.is_spoiler == False)

            stmt = stmt.order_by(desc(CommentModel.created_at)).limit(limit).offset(offset)

            rows = db.execute(stmt).all()

            if not rows:
                return []

            result: List[Comment] = []
            comment_ids = [row[0].comment_id for row in rows]

            # 좋아요 수 일괄 조회
            likes_stmt = (
                select(CommentLikeModel.comment_id, func.count(CommentLikeModel.user_id))
                .where(CommentLikeModel.comment_id.in_(comment_ids))
                .group_by(CommentLikeModel.comment_id)
            )
            likes_data = dict(db.execute(likes_stmt).all()) if comment_ids else {}

            # 현재 사용자 좋아요 여부 일괄 조회
            liked_ids = set()
            if current_user_id:
                liked_stmt = select(CommentLikeModel.comment_id).where(
                    and_(
                        CommentLikeModel.user_id == current_user_id,
                        CommentLikeModel.comment_id.in_(comment_ids),
                    )
                )
                liked_ids = set(cid for (cid,) in db.execute(liked_stmt).all())

            for comment_model, user_name, user_profile_image in rows:
                likes_count = likes_data.get(comment_model.comment_id, 0)
                is_liked = comment_model.comment_id in liked_ids if current_user_id else False

                item = self._build_comment_response(
                    comment_model,
                    user_name,
                    user_profile_image,
                    likes_count,
                    current_user_id,
                    db,
                    precomputed_is_liked=is_liked,
                )
                result.append(item)

            return result

        except Exception as e:
            return []
        finally:
            db.close()

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        db = self._get_db()
        try:
            stmt = select(CommentModel).where(CommentModel.comment_id == comment_id)
            result = db.execute(stmt)
            comment_model = result.scalar_one_or_none()

            if not comment_model:
                raise Exception("댓글을 찾을 수 없습니다")

            if comment_model.user_id != user_id:
                raise Exception("본인의 댓글만 삭제할 수 있습니다")

            # 관련 좋아요도 함께 삭제
            like_delete_stmt = CommentLikeModel.__table__.delete().where(
                CommentLikeModel.comment_id == comment_id
            )
            db.execute(like_delete_stmt)

            db.delete(comment_model)
            db.commit()

            return True

        except Exception as e:
            db.rollback()
            raise Exception(f"댓글 삭제 실패: {str(e)}")
        finally:
            db.close()

    async def like_comment(self, comment_id: int, user_id: int) -> Comment:
        db = self._get_db()
        try:
            comment_info = self._get_comment_with_user_db(comment_id, db)
            if not comment_info:
                raise Exception("댓글을 찾을 수 없습니다")

            like_stmt = select(CommentLikeModel).where(
                and_(CommentLikeModel.comment_id == comment_id, CommentLikeModel.user_id == user_id)
            )
            existing_like = db.execute(like_stmt).scalar_one_or_none()

            if not existing_like:
                new_like = CommentLikeModel(comment_id=comment_id, user_id=user_id)
                db.add(new_like)
                db.commit()

            return self._build_comment_response_from_info(comment_info, user_id, db)

        except Exception as e:
            db.rollback()
            raise Exception(f"댓글 좋아요 실패: {str(e)}")
        finally:
            db.close()

    async def unlike_comment(self, comment_id: int, user_id: int) -> Comment:
        db = self._get_db()
        try:
            comment_info = self._get_comment_with_user_db(comment_id, db)
            if not comment_info:
                raise Exception("댓글을 찾을 수 없습니다")

            like_stmt = select(CommentLikeModel).where(
                and_(CommentLikeModel.comment_id == comment_id, CommentLikeModel.user_id == user_id)
            )
            existing_like = db.execute(like_stmt).scalar_one_or_none()

            if existing_like:
                db.delete(existing_like)
                db.commit()
            # 이미 취소 상태여도 멱등적으로 통과

            return self._build_comment_response_from_info(comment_info, user_id, db)

        except Exception as e:
            db.rollback()
            raise Exception(f"댓글 좋아요 취소 실패: {str(e)}")
        finally:
            db.close()

    async def get_user_all_comments_text(self, user_id: int) -> List[str]:
        """사용자의 모든 공개 댓글 텍스트만 조회"""
        db = self._get_db()
        try:
            stmt = (
                select(CommentModel.content)
                .where(and_(CommentModel.user_id == user_id, CommentModel.is_public == True))
                .order_by(CommentModel.created_at.desc())
                .limit(20)
            )

            result = db.execute(stmt)
            comments = [row[0] for row in result]
            return comments

        except Exception:
            return []
        finally:
            db.close()

    async def get_movie_all_comments_text(self, movie_id: int) -> List[str]:
        """영화의 모든 공개 댓글 텍스트만 조회"""
        db = self._get_db()
        try:
            stmt = (
                select(CommentModel.content)
                .where(and_(CommentModel.movie_id == movie_id, CommentModel.is_public == True))
                .order_by(CommentModel.created_at.desc())
                .limit(20)
            )

            result = db.execute(stmt)
            comments = [row[0] for row in result]
            return comments

        except Exception:
            return []
        finally:
            db.close()

    # 헬퍼 메서드들 - 세션을 매개변수로 받음
    def _get_comment_with_user_db(self, comment_id: int, db: Session):
        """댓글과 사용자 정보 조회 (세션 공유)"""
        stmt = (
            select(
                CommentModel,
                UserModel.name.label("user_name"),
                UserModel.profile_image_url.label("user_profile_image"),
            )
            .join(UserModel, CommentModel.user_id == UserModel.user_id)
            .where(CommentModel.comment_id == comment_id)
        )
        return db.execute(stmt).first()

    def _build_comment_response(
        self,
        comment_model: CommentModel,
        user_name: Optional[str],
        user_profile_image: Optional[str],
        likes_count: int,
        current_user_id: Optional[int],
        db: Session,
        precomputed_is_liked: Optional[bool] = None,
    ) -> Comment:
        """통합된 댓글 응답 빌더"""
        is_liked = precomputed_is_liked if precomputed_is_liked is not None else False
        if precomputed_is_liked is None and current_user_id:
            is_liked = self._is_comment_liked_by_user_db(
                comment_model.comment_id, current_user_id, db
            )

        return Comment(
            comment_id=comment_model.comment_id,
            movie_id=comment_model.movie_id,
            user_id=comment_model.user_id,
            content=comment_model.content,
            rating=comment_model.rating,
            watched_date=comment_model.watched_date,
            is_spoiler=comment_model.is_spoiler,
            spoiler_confidence=comment_model.spoiler_confidence,
            is_positive=comment_model.is_positive,
            positive_confidence=comment_model.positive_confidence,
            is_toxic=comment_model.is_toxic,
            toxic_confidence=comment_model.toxic_confidence,
            is_public=comment_model.is_public,
            created_at=comment_model.created_at,
            updated_at=comment_model.updated_at,
            likes_count=likes_count or 0,
            is_liked=is_liked,
            user_name=user_name,
            user_profile_image=user_profile_image,
        )

    def _build_comment_response_from_info(
        self, comment_info, current_user_id: int, db: Session
    ) -> Comment:
        """댓글 정보 튜플로부터 응답 빌더"""
        comment_model, user_name, user_profile_image = comment_info
        likes_count = self._get_comment_likes_count_with_db(comment_model.comment_id, db)
        is_liked = self._is_comment_liked_by_user_db(comment_model.comment_id, current_user_id, db)

        return self._build_comment_response(
            comment_model, user_name, user_profile_image, likes_count, current_user_id, db, is_liked
        )

    def _get_comment_likes_count_with_db(self, comment_id: int, db: Session) -> int:
        """댓글의 좋아요 수 조회"""
        stmt = select(func.count(CommentLikeModel.comment_id)).where(
            CommentLikeModel.comment_id == comment_id
        )
        result = db.execute(stmt)
        return result.scalar() or 0

    def _is_comment_liked_by_user_db(self, comment_id: int, user_id: int, db: Session) -> bool:
        """사용자가 댓글을 좋아요했는지 확인"""
        stmt = select(CommentLikeModel).where(
            and_(CommentLikeModel.comment_id == comment_id, CommentLikeModel.user_id == user_id)
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none() is not None
