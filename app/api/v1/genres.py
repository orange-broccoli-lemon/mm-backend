# app/api/v1/genres.py

from typing import List
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from app.schemas.genre import Genre, GenreListResponse, GenreMovieListResponse, GenreStatsResponse, GenreWithMovieCount
from app.services.genre_service import GenreService
from app.services.tmdb_service import TMDBService

router = APIRouter()

def get_genre_service() -> GenreService:
    return GenreService()

def get_tmdb_service() -> TMDBService:
    return TMDBService()

@router.get(
    "/",
    response_model=GenreListResponse,
    summary="모든 장르 조회",
    description="데이터베이스에 저장된 모든 장르 목록을 조회합니다."
)
async def get_all_genres(
    genre_service: GenreService = Depends(get_genre_service)
):
    try:
        genres = await genre_service.get_all_genres()
        return genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/stats",
    response_model=GenreStatsResponse,
    summary="장르별 통계",
    description="각 장르별 영화 수 통계를 조회합니다."
)
async def get_genre_stats(
    genre_service: GenreService = Depends(get_genre_service)
):
    try:
        stats = await genre_service.get_genre_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/popular",
    response_model=List[GenreWithMovieCount],
    summary="인기 장르 조회",
    description="영화 수가 많은 순서대로 인기 장르를 조회합니다."
)
async def get_popular_genres(
    limit: int = Query(default=10, ge=1, le=50, description="조회할 장르 수"),
    genre_service: GenreService = Depends(get_genre_service)
):
    try:
        popular_genres = await genre_service.get_popular_genres(limit)
        return popular_genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/search",
    response_model=List[Genre],
    summary="장르 검색",
    description="장르 이름으로 검색합니다."
)
async def search_genres(
    query: str = Query(description="검색할 장르 이름"),
    genre_service: GenreService = Depends(get_genre_service)
):
    try:
        genres = await genre_service.search_genres(query)
        return genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{genre_id}",
    response_model=Genre,
    summary="특정 장르 조회",
    description="장르 ID로 특정 장르 정보를 조회합니다."
)
async def get_genre_by_id(
    genre_id: int = Path(description="장르 ID"),
    genre_service: GenreService = Depends(get_genre_service)
):
    try:
        genre = await genre_service.get_genre_by_id(genre_id)
        if not genre:
            raise HTTPException(status_code=404, detail="장르를 찾을 수 없습니다")
        return genre
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{genre_id}/movies",
    response_model=GenreMovieListResponse,
    summary="장르별 영화 목록",
    description="특정 장르에 속한 영화 목록을 조회합니다."
)
async def get_movies_by_genre(
    genre_id: int = Path(description="장르 ID"),
    skip: int = Query(default=0, ge=0, description="건너뛸 영화 수"),
    limit: int = Query(default=20, ge=1, le=100, description="가져올 영화 수"),
    genre_service: GenreService = Depends(get_genre_service)
):
    try:
        movies = await genre_service.get_movies_by_genre(genre_id, skip, limit)
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/tmdb/movies",
    summary="TMDB 장르 목록",
    description="TMDB에서 영화 장르 목록을 가져옵니다."
)
async def get_tmdb_movie_genres(
    language: str = Query(default="ko-KR", regex="^[a-z]{2}-[A-Z]{2}$"),
    tmdb_service: TMDBService = Depends(get_tmdb_service)
):
    try:
        genres = await tmdb_service.get_movie_genres(language)
        return genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/sync-tmdb",
    summary="TMDB 장르 동기화",
    description="TMDB에서 장르 목록을 가져와 데이터베이스에 저장합니다."
)
async def sync_genres_from_tmdb(
    language: str = Query(default="ko-KR", regex="^[a-z]{2}-[A-Z]{2}$"),
    genre_service: GenreService = Depends(get_genre_service),
    tmdb_service: TMDBService = Depends(get_tmdb_service)
):
    try:
        # TMDB에서 장르 목록 가져오기
        tmdb_genres = await tmdb_service.get_movie_genres(language)
        
        # 데이터베이스에 저장
        created_genres = []
        for tmdb_genre in tmdb_genres.get("genres", []):
            genre = await genre_service.create_genre(
                tmdb_genre["id"], 
                tmdb_genre["name"]
            )
            created_genres.append(genre)
        
        return {
            "message": f"{len(created_genres)}개의 장르가 동기화되었습니다",
            "genres": created_genres
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
