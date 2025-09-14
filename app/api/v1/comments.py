# app/api/v1/comments.py

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Path
from app.schemas.comment import Comment, CommentCreate, CommentUpdate
from app.schemas.user import User
from app.services.comment_service import CommentService
from app.core.dependencies import get_current_user

router = APIRouter()

def get_comment_service() -> CommentService:
    return CommentService()

# 선택적 인증
async def get_current_user_optional() -> Optional[User]:
    try:
        from fastapi import Request
        from fastapi.security import HTTPBearer
        security = HTTPBearer(auto_error=False)
        
        # 토큰이 없어도 에러 발생하지 않음
        return None
    except:
        return None

@router.post(
    "/",
    response_model=Comment,
    summary="댓글 작성",
    description="영화에 댓글을 작성합니다."
)
async def create_comment(
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service)
):
    try:
        comment = await comment_service.create_comment(comment_data, current_user.user_id)
        return comment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/movie/{movie_id}",
    response_model=List[Comment],
    summary="영화 댓글 조회",
    description="특정 영화의 모든 댓글을 조회합니다."
)
async def get_movie_comments(
    movie_id: int = Path(description="영화 ID"),
    comment_service: CommentService = Depends(get_comment_service)
):
    try:
        # 로그인하지 않아도 댓글 조회 가능
        comments = await comment_service.get_movie_comments(movie_id, None)
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/movie/{movie_id}/authenticated",
    response_model=List[Comment],
    summary="영화 댓글 조회 (인증)",
    description="로그인한 사용자의 좋아요 정보를 포함한 댓글 조회"
)
async def get_movie_comments_authenticated(
    movie_id: int = Path(description="영화 ID"),
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service)
):
    try:
        comments = await comment_service.get_movie_comments(movie_id, current_user.user_id)
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/{comment_id}",
    response_model=Comment,
    summary="댓글 수정",
    description="자신의 댓글을 수정합니다."
)
async def update_comment(
    comment_id: int = Path(description="댓글 ID"),
    comment_data: CommentUpdate = ...,
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service)
):
    try:
        comment = await comment_service.update_comment(comment_id, comment_data, current_user.user_id)
        return comment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete(
    "/{comment_id}",
    summary="댓글 삭제",
    description="자신의 댓글을 삭제합니다."
)
async def delete_comment(
    comment_id: int = Path(description="댓글 ID"),
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service)
):
    try:
        success = await comment_service.delete_comment(comment_id, current_user.user_id)
        return {"message": "댓글이 삭제되었습니다", "success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/{comment_id}/toggle-like",
    response_model=Comment,
    summary="댓글 좋아요 토글",
    description="댓글 좋아요를 추가하거나 취소합니다."
)
async def toggle_like_comment(
    comment_id: int = Path(description="댓글 ID"),
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service)
):
    try:
        comment = await comment_service.toggle_like_comment(comment_id, current_user.user_id)
        return comment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
