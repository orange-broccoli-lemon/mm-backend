from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc
from app.models.comment import CommentModel
from app.models.comment_like import CommentLikeModel
from app.models.user import UserModel
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
                rating=comment_data.rating,
                watched_date=comment_data.watched_date,
                is_spoiler=comment_data.is_spoiler,
                spoiler_confidence=comment_data.spoiler_confidence,
                is_public=comment_data.is_public
            )
            
            self.db.add(comment_model)
            self.db.commit()
            self.db.refresh(comment_model)
            
            # 사용자 정보 조회
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_result = self.db.execute(user_stmt)
            user_model = user_result.scalar_one_or_none()
            
            comment_dict = {
                'comment_id': comment_model.comment_id,
                'movie_id': comment_model.movie_id,
                'user_id': comment_model.user_id,
                'content': comment_model.content,
                'rating': comment_model.rating,
                'watched_date': comment_model.watched_date,
                'is_spoiler': comment_model.is_spoiler,
                'spoiler_confidence': comment_model.spoiler_confidence,
                'is_public': comment_model.is_public,
                'created_at': comment_model.created_at,
                'updated_at': comment_model.updated_at,
                'likes_count': 0,
                'is_liked': False,
                'user_name': user_model.name if user_model else None,
                'user_profile_image': user_model.profile_image_url if user_model else None
            }
            
            return Comment(**comment_dict)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"댓글 작성 실패: {str(e)}")
    
    async def get_movie_comments(
        self, 
        movie_id: int, 
        current_user_id: Optional[int] = None,
        include_spoilers: bool = False,
        limit: int = 20, 
        offset: int = 0
    ) -> List[Comment]:
        try:
            # 사용자 정보와 좋아요 수를 함께 조회
            stmt = select(
                CommentModel,
                UserModel.name.label('user_name'),
                UserModel.profile_image_url.label('user_profile_image'),
                func.count(CommentLikeModel.comment_id).label('likes_count')
            ).join(
                UserModel, CommentModel.user_id == UserModel.user_id
            ).outerjoin(
                CommentLikeModel, CommentModel.comment_id == CommentLikeModel.comment_id
            ).where(
                and_(
                    CommentModel.movie_id == movie_id,
                    CommentModel.is_public == True  # 공개 댓글만
                )
            )
            
            # 스포일러 필터링
            if not include_spoilers:
                stmt = stmt.where(CommentModel.is_spoiler == False)
            
            stmt = stmt.group_by(
                CommentModel.comment_id,
                UserModel.name,
                UserModel.profile_image_url
            ).order_by(desc(CommentModel.created_at)).limit(limit).offset(offset)
            
            result = self.db.execute(stmt)
            comments_with_info = result.all()
            
            comment_list = []
            for comment_model, user_name, user_profile_image, likes_count in comments_with_info:
                is_liked = False
                if current_user_id:
                    is_liked = self._is_comment_liked_by_user(comment_model.comment_id, current_user_id)
                
                comment_dict = {
                    'comment_id': comment_model.comment_id,
                    'movie_id': comment_model.movie_id,
                    'user_id': comment_model.user_id,
                    'content': comment_model.content,
                    'rating': comment_model.rating,
                    'watched_date': comment_model.watched_date,
                    'is_spoiler': comment_model.is_spoiler,
                    'spoiler_confidence': comment_model.spoiler_confidence,
                    'is_public': comment_model.is_public,
                    'created_at': comment_model.created_at,
                    'updated_at': comment_model.updated_at,
                    'likes_count': likes_count or 0,
                    'is_liked': is_liked,
                    'user_name': user_name,
                    'user_profile_image': user_profile_image
                }
                
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
            if comment_data.rating is not None:
                comment_model.rating = comment_data.rating
            if comment_data.watched_date is not None:
                comment_model.watched_date = comment_data.watched_date
            if comment_data.is_spoiler is not None:
                comment_model.is_spoiler = comment_data.is_spoiler
            if comment_data.spoiler_confidence is not None:
                comment_model.spoiler_confidence = comment_data.spoiler_confidence
            if comment_data.is_public is not None:
                comment_model.is_public = comment_data.is_public
            
            self.db.commit()
            self.db.refresh(comment_model)
            
            # 사용자 정보 조회
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user_result = self.db.execute(user_stmt)
            user_model = user_result.scalar_one_or_none()
            
            # 좋아요 수와 현재 사용자 좋아요 여부 계산
            likes_count = self._get_comment_likes_count(comment_id)
            is_liked = self._is_comment_liked_by_user(comment_id, user_id)
            
            comment_dict = {
                'comment_id': comment_model.comment_id,
                'movie_id': comment_model.movie_id,
                'user_id': comment_model.user_id,
                'content': comment_model.content,
                'rating': comment_model.rating,
                'watched_date': comment_model.watched_date,
                'is_spoiler': comment_model.is_spoiler,
                'spoiler_confidence': comment_model.spoiler_confidence,
                'is_public': comment_model.is_public,
                'created_at': comment_model.created_at,
                'updated_at': comment_model.updated_at,
                'likes_count': likes_count,
                'is_liked': is_liked,
                'user_name': user_model.name if user_model else None,
                'user_profile_image': user_model.profile_image_url if user_model else None
            }
            
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
            # 댓글 존재 확인 및 사용자 정보 조회
            comment_stmt = select(
                CommentModel,
                UserModel.name.label('user_name'),
                UserModel.profile_image_url.label('user_profile_image')
            ).join(
                UserModel, CommentModel.user_id == UserModel.user_id
            ).where(CommentModel.comment_id == comment_id)
            
            comment_result = self.db.execute(comment_stmt)
            comment_info = comment_result.first()
            
            if not comment_info:
                raise Exception("댓글을 찾을 수 없습니다")
            
            comment_model = comment_info[0]
            user_name = comment_info[1]
            user_profile_image = comment_info[2]
            
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
            
            comment_dict = {
                'comment_id': comment_model.comment_id,
                'movie_id': comment_model.movie_id,
                'user_id': comment_model.user_id,
                'content': comment_model.content,
                'rating': comment_model.rating,
                'watched_date': comment_model.watched_date,
                'is_spoiler': comment_model.is_spoiler,
                'spoiler_confidence': comment_model.spoiler_confidence,
                'is_public': comment_model.is_public,
                'created_at': comment_model.created_at,
                'updated_at': comment_model.updated_at,
                'likes_count': likes_count,
                'is_liked': is_liked,
                'user_name': user_name,
                'user_profile_image': user_profile_image
            }
            
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
