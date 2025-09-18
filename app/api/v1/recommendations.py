# app/api/v1/recommendations.py

from fastapi import APIRouter, HTTPException, Depends, status
from app.services.recommendation_service import RecommendationService
from app.core.dependencies import get_current_user
from app.models import UserModel as User

router = APIRouter()


def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


@router.get(
    "/movies",
    summary="영화 추천",
    description="사용자의 시청 기록을 기반으로 영화를 추천합니다.",
)
async def get_movie_recommendations(
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """개인화된 영화 추천"""
    try:
        recommendations = await recommendation_service.get_movie_recommendations(
            user_id=current_user.user_id, min_rating=1.0
        )

        return {"user_id": current_user.user_id, "recommendations": recommendations}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"영화 추천 실패: {str(e)}"
        )
