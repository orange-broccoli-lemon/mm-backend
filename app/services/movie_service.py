# app/services/movie_service.py

from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import ProgrammingError
from app.models.movie import MovieModel
from app.schemas import Movie
from app.database import get_db

class MovieService:
    
    def __init__(self):
        self.db: Session = next(get_db())
    
    async def get_movie_by_movie_id(self, movie_id: int) -> Optional[Movie]:
        try:
            print(f"DB 조회 시작: {movie_id}")
            
            stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
            result = self.db.execute(stmt)
            movie_model = result.scalar_one_or_none()
            
            if movie_model:
                print(f"DB에서 영화 발견: {movie_model.title}")
                return Movie.from_orm(movie_model)
            
            print("DB에 영화 없음")
            return None
            
        except Exception as e:
            print(f"DB 조회 실패: {str(e)}")
            raise Exception(f"데이터베이스 조회 실패: {str(e)}")
    
    async def save_movie_from_tmdb_data(self, tmdb_data: dict) -> Movie:
        try:
            movie_id = tmdb_data.get("id")
            print(f"TMDB 데이터 저장 시작 - ID: {movie_id}")
            
            existing_movie = await self.get_movie_by_movie_id(movie_id)
            if existing_movie:
                print("이미 DB에 존재함")
                return existing_movie
            
            movie_model = MovieModel(
                movie_id=movie_id,
                title=tmdb_data.get("title", ""),
                original_title=tmdb_data.get("original_title"),
                overview=tmdb_data.get("overview"),
                release_date=self._parse_date(tmdb_data.get("release_date")),
                runtime=tmdb_data.get("runtime"),
                poster_url=self._build_image_url(tmdb_data.get("poster_path"), "w500"),
                backdrop_url=self._build_image_url(tmdb_data.get("backdrop_path"), "w1280"),
                average_rating=Decimal(str(tmdb_data.get("vote_average", 0.0))),
                is_adult=tmdb_data.get("adult", False),
                trailer_url=self._extract_trailer_url(tmdb_data)
            )
            
            self.db.add(movie_model)
            self.db.commit()
            self.db.refresh(movie_model)
            
            print(f"DB 저장 완료: {movie_model.movie_id}")
            return Movie.from_orm(movie_model)
            
        except Exception as e:
            self.db.rollback()
            print(f"DB 저장 실패: {str(e)}")
            raise Exception(f"데이터베이스 저장 실패: {str(e)}")
    
    async def get_all_movies(self, skip: int = 0, limit: int = 100) -> List[Movie]:
        try:
            stmt = select(MovieModel).offset(skip).limit(limit).order_by(MovieModel.created_at.desc())
            result = self.db.execute(stmt)
            movies = result.scalars().all()
            
            return [Movie.from_orm(movie) for movie in movies]
            
        except Exception as e:
            raise Exception(f"영화 목록 조회 실패: {str(e)}")

    async def get_movies_count(self) -> int:
        try:
            stmt = select(func.count(MovieModel.movie_id))
            result = self.db.execute(stmt)
            return result.scalar() or 0
            
        except Exception as e:
            raise Exception(f"영화 개수 조회 실패: {str(e)}")
    
    def _parse_date(self, date_str: Optional[str]):
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    
    def _build_image_url(self, path: Optional[str], size: str) -> Optional[str]:
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/{size}{path}"
    
    def _extract_trailer_url(self, movie_data: dict) -> Optional[str]:
        videos = movie_data.get("videos", {}).get("results", [])
        for video in videos:
            if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                return f"https://www.youtube.com/watch?v={video.get('key')}"
        return None
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
