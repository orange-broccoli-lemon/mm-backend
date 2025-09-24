# app/api/v1/ai.py

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from app.ai import findbot
from app.services.movie_service import MovieService
from app.services.tmdb_service import TMDBService
from app.schemas.ai import (
    FindBotRequest,
    FindBotResponse,
)

router = APIRouter()


def get_movie_service() -> MovieService:
    return MovieService()


def get_tmdb_service() -> TMDBService:
    return TMDBService()


@router.post(
    "/findbot",
    response_model=FindBotResponse,
    summary="AI 영화 찾기",
    description="단서를 제공하면 AI가 영화를 찾습니다.",
)
async def find_movie(
    request: FindBotRequest,
    movie_service: MovieService = Depends(get_movie_service),
    tmdb_service: TMDBService = Depends(get_tmdb_service),
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

        # 4. AI가 찾은 영화 정보
        ai_movie_title = result.get("title")
        ai_movie_id = result.get("movie_id")

        if not ai_movie_title or not ai_movie_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI 응답에 영화 제목 또는 ID가 없습니다",
            )

        # 5. TMDB에서 영화 제목으로 검색하여 ID 검증
        verified_movie_id = ai_movie_id

        try:
            print(f"TMDB에서 영화 검색 시작: {ai_movie_title}")
            search_results = await tmdb_service.search_movie_by_title(ai_movie_title)

            if search_results:
                matched_id = tmdb_service.find_best_movie_match(search_results, ai_movie_title)
                if matched_id:
                    verified_movie_id = matched_id
                    print(f"TMDB 검색으로 검증된 영화 ID: {verified_movie_id}")
                else:
                    print(f"TMDB 검색에서 매치되는 영화를 찾지 못함. AI ID 사용: {ai_movie_id}")
            else:
                print(f"TMDB 검색 결과 없음. AI ID 사용: {ai_movie_id}")

        except Exception as search_error:
            print(f"TMDB 검색 중 오류 발생: {str(search_error)}")
            print(f"AI가 찾은 ID 사용: {ai_movie_id}")

        # 6. 검증된 ID로 DB에 영화 저장
        try:
            await movie_service.get_movie_detail(verified_movie_id)
            print(f"영화 DB 저장 완료: {verified_movie_id}")
        except Exception as db_error:
            print(f"영화 DB 저장 실패: {str(db_error)}")

        # 7. 성공 응답 반환
        return FindBotResponse(
            success=True,
            title=ai_movie_title,
            movie_id=verified_movie_id,
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
