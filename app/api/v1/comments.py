from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from app.schemas.comment import Comment, CommentCreate, CommentUpdate
from app.schemas.user import User
from app.services.comment_service import CommentService
from app.core.dependencies import get_current_user, get_optional_current_user

router = APIRouter()


def get_comment_service() -> CommentService:
    return CommentService()


@router.get(
    "/{comment_id}",
    response_model=Comment,
    summary="댓글 단건 조회",
    description="comment_id로 댓글을 조회합니다.",
)
async def get_comment_by_id(
    comment_id: int = Path(description="댓글 ID"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    try:
        current_user_id = current_user.user_id if current_user else None
        return await comment_service.get_comment(comment_id, current_user_id)
    except Exception as e:
        msg = str(e)
        if "찾을 수 없습니다" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)


@router.put(
    "/{comment_id}",
    response_model=Comment,
    summary="댓글 수정",
    description="자신의 댓글을 수정합니다.",
)
async def update_comment(
    comment_id: int = Path(description="댓글 ID"),
    comment_data: CommentUpdate = ...,
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    try:
        return await comment_service.update_comment(comment_id, comment_data, current_user.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{comment_id}", summary="댓글 삭제", description="자신의 댓글을 삭제합니다.")
async def delete_comment(
    comment_id: int = Path(description="댓글 ID"),
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    try:
        success = await comment_service.delete_comment(comment_id, current_user.user_id)
        return {"message": "댓글이 삭제되었습니다", "success": success}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{comment_id}/like",
    response_model=Comment,
    summary="댓글 좋아요",
    description="댓글에 좋아요를 추가합니다.",
)
async def like_comment(
    comment_id: int = Path(description="댓글 ID"),
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    try:
        return await comment_service.like_comment(comment_id, current_user.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{comment_id}/like", summary="댓글 좋아요 취소", description="댓글 좋아요를 취소합니다."
)
async def unlike_comment(
    comment_id: int = Path(description="댓글 ID"),
    current_user: User = Depends(get_current_user),
    comment_service: CommentService = Depends(get_comment_service),
):
    try:
        comment = await comment_service.unlike_comment(comment_id, current_user.user_id)
        return {"message": "좋아요 취소 완료", "success": True, "comment": comment}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
