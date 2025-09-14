# app/services/comment_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from app.models.comment import CommentModel
from app.models.comment_like import CommentLikeModel
from app.schemas.comment import Comment, CommentCreate, CommentUpdate
from app.database import get_db

class CommentService:
    
    def __init__(self):
        self.db: Session = next(get_db())
    
    async def create_comment(self, comment_data: CommentCreate, user_id: int) -> Comment:
        try:
            comment_model = CommentModel(
                movie_id=comment_data.movie_id,
                user_id=user_id,
                content=comment_data.content,
                is_spoiler=comment_data.is_spoiler,
                spoiler_confidence=comment_data.spoiler_confidence
            )
            
            self.db.add(comment_model)
            self.db.commit()
            self.db.refresh(comment_model)
            
            # 좋아요 수와 현재 사용자 좋아요 여부 계산
            comment_dict = comment_model.__dict__.copy()
            comment_dict['likes_count'] = 0
            comment_dict['is_liked'] = False
            
            return Comment(**comment_dict)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"댓글 작성 실패: {str(e)}")
    
    async def get_movie_comments(self, movie_id: int, current_user_id: Optional[int] = None) -> List[Comment]:
        try:
            # 댓글과 좋아요 수를 함께 조회
            stmt = select(
                CommentModel,
                func.count(CommentLikeModel.comment_id).label('likes_count')
            ).outerjoin(
                CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id
            ).where(
                CommentModel.movie_id == movie_id
            ).group_by(CommentModel.comment_id)
            
            result = self.db.execute(stmt)
            comments_with_likes = result.all()
            
            comment_list = []
            for comment_model, likes_count in comments_with_likes:
                # 현재 사용자의 좋아요 여부 확인
                is_liked = False
                if current_user_id:
                    like_stmt = select(CommentLikeModel).where(
                        and_(
                            CommentLikeModel.comment_id == comment_model.comment_id,
                            CommentLikeModel.user_id == current_user_id
                        )
                    )
                    like_result = self.db.execute(like_stmt)
                    is_liked = like_result.scalar_one_or_none() is not None
                
                comment_dict = comment_model.__dict__.copy()
                comment_dict['likes_count'] = likes_count or 0
                comment_dict['is_liked'] = is_liked
                
                comment_list.append(Comment(**comment_dict))
            
            return comment_list
            
        except Exception as e:
            raise Exception(f"댓글 조회 실패: {str(e)}")
    
    async def update_comment(self, comment_id: int, comment_data: CommentUpdate, user_id: int) -> Comment:
        try:
            stmt = select(CommentModel).where(CommentModel.comment_id == comment_id)
            result = self.db.execute(stmt)
            comment_model = result.scalar_one_or_none()
            
            if not comment_model:
                raise Exception("댓글을 찾을 수 없습니다")
            
            if comment_model.user_id != user_id:
                raise Exception("본인의 댓글만 수정할 수 있습니다")
            
            # 업데이트할 필드만 변경
            if comment_data.content is not None:
                comment_model.content = comment_data.content
            if comment_data.is_spoiler is not None:
                comment_model.is_spoiler = comment_data.is_spoiler
            if comment_data.spoiler_confidence is not None:
                comment_model.spoiler_confidence = comment_data.spoiler_confidence
            
            self.db.commit()
            self.db.refresh(comment_model)
            
            # 좋아요 수와 현재 사용자 좋아요 여부 계산
            likes_count = self._get_comment_likes_count(comment_id)
            is_liked = self._is_comment_liked_by_user(comment_id, user_id)
            
            comment_dict = comment_model.__dict__.copy()
            comment_dict['likes_count'] = likes_count
            comment_dict['is_liked'] = is_liked
            
            return Comment(**comment_dict)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"댓글 수정 실패: {str(e)}")
    
    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        try:
            stmt = select(CommentModel).where(CommentModel.comment_id == comment_id)
            result = self.db.execute(stmt)
            comment_model = result.scalar_one_or_none()
            
            if not comment_model:
                raise Exception("댓글을 찾을 수 없습니다")
            
            if comment_model.user_id != user_id:
                raise Exception("본인의 댓글만 삭제할 수 있습니다")
            
            # 관련 좋아요도 함께 삭제
            like_delete_stmt = CommentLikeModel.__table__.delete().where(
                CommentLikeModel.comment_id == comment_id
            )
            self.db.execute(like_delete_stmt)
            
            self.db.delete(comment_model)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"댓글 삭제 실패: {str(e)}")
    
    async def toggle_like_comment(self, comment_id: int, user_id: int) -> Comment:
        try:
            # 댓글 존재 확인
            comment_stmt = select(CommentModel).where(CommentModel.comment_id == comment_id)
            comment_result = self.db.execute(comment_stmt)
            comment_model = comment_result.scalar_one_or_none()
            
            if not comment_model:
                raise Exception("댓글을 찾을 수 없습니다")
            
            # 기존 좋아요 확인
            like_stmt = select(CommentLikeModel).where(
                and_(
                    CommentLikeModel.comment_id == comment_id,
                    CommentLikeModel.user_id == user_id
                )
            )
            like_result = self.db.execute(like_stmt)
            existing_like = like_result.scalar_one_or_none()
            
            if existing_like:
                # 좋아요 취소
                self.db.delete(existing_like)
                is_liked = False
            else:
                # 좋아요 추가
                new_like = CommentLikeModel(
                    comment_id=comment_id,
                    user_id=user_id
                )
                self.db.add(new_like)
                is_liked = True
            
            self.db.commit()
            
            # 업데이트된 좋아요 수 계산
            likes_count = self._get_comment_likes_count(comment_id)
            
            comment_dict = comment_model.__dict__.copy()
            comment_dict['likes_count'] = likes_count
            comment_dict['is_liked'] = is_liked
            
            return Comment(**comment_dict)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"댓글 좋아요 처리 실패: {str(e)}")
    
    def _get_comment_likes_count(self, comment_id: int) -> int:
        """댓글의 좋아요 수 조회"""
        stmt = select(func.count(CommentLikeModel.comment_id)).where(
            CommentLikeModel.comment_id == comment_id
        )
        result = self.db.execute(stmt)
        return result.scalar() or 0
    
    def _is_comment_liked_by_user(self, comment_id: int, user_id: int) -> bool:
        """사용자가 댓글을 좋아요했는지 확인"""
        stmt = select(CommentLikeModel).where(
            and_(
                CommentLikeModel.comment_id == comment_id,
                CommentLikeModel.user_id == user_id
            )
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
