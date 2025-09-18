# app/api/v1/ai.py

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from app.ai import findbot
from app.services.movie_service import MovieService
from app.schemas.ai import (
    FindBotRequest,
    FindBotResponse,
)

router = APIRouter()


def get_movie_service() -> MovieService:
    return MovieService()


def get_movie_service() -> MovieService:
    return MovieService()


@router.post(
    "/findbot",
    response_model=FindBotResponse,
    summary="AI 영화 찾기",
    description="단서를 제공하면 AI가 영화를 찾습니다.",
)
async def find_movie(
    request: FindBotRequest,
    movie_service: MovieService = Depends(get_movie_service),
):
    """AI 영화 찾기"""
    try:
        # 1. AI에게 영화 찾기 요청
        ai_response = await findbot(request.query)

        # 2. JSON 파싱
        try:
            result = json.loads(ai_response)
        except json.JSONDecodeError as parse_error:
            print(f"JSON 파싱 에러: {str(parse_error)}")
            print(f"파싱 실패한 응답: {ai_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI 응답 파싱 실패: {str(parse_error)}",
            )

        # 3. 실패한 경우 그대로 반환
        if not result.get("success", False):
            return FindBotResponse(
                success=False, message=result.get("message", "영화를 찾을 수 없습니다")
            )

        # 4. 성공한 경우 DB에 영화 저장
        movie_id = result.get("movie_id")
        if not movie_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TMDB ID가 응답에 없습니다",
            )

        try:
            # MovieService를 통해 영화 상세 정보 조회
            await movie_service.get_movie_detail(movie_id)
            print(f"영화 DB 저장 완료: {movie_id}")
        except Exception as db_error:
            print(f"영화 DB 저장 실패: {str(db_error)}")
            # DB 저장 실패해도 AI 응답은 반환

        # 5. 성공 응답 반환
        return FindBotResponse(
            success=True,
            title=result.get("title"),
            movie_id=movie_id,
            reason=result.get("reason"),
            plot=result.get("plot"),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"findbot API 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"영화 찾기 실패: {str(e)}"
        )
