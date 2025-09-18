from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from app.services.scheduler_service import SchedulerService
from app.services.user_service import UserService
from app.services.movie_service import MovieService
from app.services.comment_service import CommentService
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models import UserModel as User

router = APIRouter()


@router.post(
    "/test/profile-analysis",
    summary="테스트: 사용자 프로필 분석",
    description="테스트용: 사용자 프로필 분석을 즉시 실행합니다.",
)
async def test_profile_analysis(
    background_tasks: BackgroundTasks, current_user: User = Depends(get_optional_current_user)
):
    """테스트용 사용자 프로필 분석"""
    try:
        scheduler_service = SchedulerService()

        # 백그라운드 작업으로 실행
        background_tasks.add_task(scheduler_service.daily_profile_analysis)

        return {
            "message": "사용자 프로필 분석이 백그라운드에서 시작되었습니다",
            "status": "started",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로필 분석 실행 실패: {str(e)}",
        )


@router.post(
    "/test/movie-review-analysis",
    summary="테스트: 영화 리뷰 분석",
    description="테스트용: 영화 리뷰 분석을 즉시 실행합니다.",
)
async def test_movie_review_analysis(
    background_tasks: BackgroundTasks, current_user: User = Depends(get_optional_current_user)
):
    """테스트용 영화 리뷰 분석"""
    try:
        scheduler_service = SchedulerService()

        # 백그라운드 작업으로 실행
        background_tasks.add_task(scheduler_service.daily_movie_review_analysis)

        return {"message": "영화 리뷰 분석이 백그라운드에서 시작되었습니다", "status": "started"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"영화 리뷰 분석 실행 실패: {str(e)}",
        )


@router.post(
    "/test/full-ai-analysis",
    summary="테스트: 전체 AI 분석",
    description="테스트용: 사용자 프로필 + 영화 리뷰 분석을 모두 실행합니다.",
)
async def test_full_ai_analysis(
    background_tasks: BackgroundTasks, current_user: User = Depends(get_optional_current_user)
):
    """테스트용 전체 AI 분석"""
    try:
        scheduler_service = SchedulerService()

        # 백그라운드 작업으로 실행
        background_tasks.add_task(scheduler_service.daily_ai_analysis)

        return {"message": "전체 AI 분석이 백그라운드에서 시작되었습니다", "status": "started"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"전체 AI 분석 실행 실패: {str(e)}",
        )


@router.get(
    "/test/users-with-comments",
    summary="테스트: 댓글 있는 사용자 조회",
    description="댓글이 5개 이상인 사용자 목록을 조회합니다.",
)
async def test_users_with_comments(
    min_comments: int = 5, current_user: User = Depends(get_optional_current_user)
):
    """댓글 있는 사용자 목록 조회"""
    try:
        user_service = UserService()
        users = await user_service.get_users_with_comments(min_comments=min_comments)

        return {"total_users": len(users), "users": users}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 조회 실패: {str(e)}"
        )


@router.get(
    "/test/movies-with-comments",
    summary="테스트: 댓글 있는 영화 조회",
    description="댓글이 5개 이상인 영화 목록을 조회합니다.",
)
async def test_movies_with_comments(
    min_comments: int = 5, current_user: User = Depends(get_optional_current_user)
):
    """댓글 있는 영화 목록 조회"""
    try:
        movie_service = MovieService()
        movies = await movie_service.get_movies_with_comments(min_comments=min_comments)

        return {"total_movies": len(movies), "movies": movies}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"영화 조회 실패: {str(e)}"
        )


@router.get(
    "/test/user-comments/{user_id}",
    summary="테스트: 특정 사용자 댓글 조회",
    description="특정 사용자의 댓글 텍스트를 조회합니다.",
)
async def test_user_comments(user_id: int, current_user: User = Depends(get_optional_current_user)):
    """특정 사용자 댓글 조회"""
    try:
        comment_service = CommentService()
        comments = await comment_service.get_user_all_comments_text(user_id)

        return {"user_id": user_id, "total_comments": len(comments), "comments": comments}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"댓글 조회 실패: {str(e)}"
        )


@router.get(
    "/test/movie-comments/{movie_id}",
    summary="테스트: 특정 영화 댓글 조회",
    description="특정 영화의 댓글 텍스트를 조회합니다.",
)
async def test_movie_comments(
    movie_id: int, current_user: User = Depends(get_optional_current_user)
):
    """특정 영화 댓글 조회"""
    try:
        comment_service = CommentService()
        comments = await comment_service.get_movie_all_comments_text(movie_id)

        return {"movie_id": movie_id, "total_comments": len(comments), "comments": comments}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"댓글 조회 실패: {str(e)}"
        )


@router.get(
    "/test/scheduler-status",
    summary="테스트: 스케줄러 상태",
    description="현재 스케줄러 상태를 확인합니다.",
)
async def test_scheduler_status():
    """스케줄러 상태 확인"""
    from app.main import scheduler_task

    return {
        "scheduler_exists": scheduler_task is not None,
        "scheduler_running": (
            scheduler_task and not scheduler_task.done() if scheduler_task else False
        ),
        "scheduler_cancelled": scheduler_task.cancelled() if scheduler_task else False,
        "scheduler_exception": (
            str(scheduler_task.exception())
            if scheduler_task and scheduler_task.done() and scheduler_task.exception()
            else None
        ),
    }
