# app/services/movie_service.py

from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import ProgrammingError
from app.models.movie import MovieModel
from app.models.genre import GenreModel
from app.models.movie_genre import MovieGenreModel
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
                # 기존 영화도 장르 연결 확인/추가
                await self._save_movie_genres(movie_id, tmdb_data.get("genres", []))
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
            
            # 장르 정보 저장
            await self._save_movie_genres(movie_id, tmdb_data.get("genres", []))
            
            print(f"DB 저장 완료: {movie_model.movie_id} (장르 포함)")
            return Movie.from_orm(movie_model)
            
        except Exception as e:
            self.db.rollback()
            print(f"DB 저장 실패: {str(e)}")
            raise Exception(f"데이터베이스 저장 실패: {str(e)}")
    
    async def _save_movie_genres(self, movie_id: int, genres: List[dict]):
        """영화의 장르 정보를 저장"""
        try:
            for genre_data in genres:
                genre_id = genre_data.get("id")
                genre_name = genre_data.get("name")
                
                if not genre_id or not genre_name:
                    continue
                
                # 장르가 DB에 없으면 생성
                await self._ensure_genre_exists(genre_id, genre_name)
                
                # 영화-장르 연결이 없으면 생성
                await self._ensure_movie_genre_connection(movie_id, genre_id)
                
        except Exception as e:
            print(f"장르 저장 실패: {str(e)}")
            # 장르 저장 실패는 영화 저장을 막지 않음
    
    async def _ensure_genre_exists(self, genre_id: int, genre_name: str):
        """장르가 DB에 존재하는지 확인하고 없으면 생성"""
        try:
            stmt = select(GenreModel).where(GenreModel.genre_id == genre_id)
            result = self.db.execute(stmt)
            existing_genre = result.scalar_one_or_none()
            
            if not existing_genre:
                new_genre = GenreModel(
                    genre_id=genre_id,
                    name=genre_name
                )
                self.db.add(new_genre)
                self.db.commit()
                print(f"새 장르 생성: {genre_name} (ID: {genre_id})")
            
        except Exception as e:
            self.db.rollback()
            print(f"장르 생성 실패: {str(e)}")
    
    async def _ensure_movie_genre_connection(self, movie_id: int, genre_id: int):
        """영화-장르 연결이 존재하는지 확인하고 없으면 생성"""
        try:
            stmt = select(MovieGenreModel).where(
                MovieGenreModel.movie_id == movie_id,
                MovieGenreModel.genre_id == genre_id
            )
            result = self.db.execute(stmt)
            existing_connection = result.scalar_one_or_none()
            
            if not existing_connection:
                new_connection = MovieGenreModel(
                    movie_id=movie_id,
                    genre_id=genre_id
                )
                self.db.add(new_connection)
                self.db.commit()
                print(f"영화-장르 연결 생성: 영화({movie_id}) - 장르({genre_id})")
            
        except Exception as e:
            self.db.rollback()
            print(f"영화-장르 연결 실패: {str(e)}")
    
    async def get_movie_genres(self, movie_id: int) -> List[dict]:
        """영화의 장르 목록 조회"""
        try:
            stmt = select(GenreModel).join(
                MovieGenreModel, GenreModel.genre_id == MovieGenreModel.genre_id
            ).where(MovieGenreModel.movie_id == movie_id)
            
            result = self.db.execute(stmt)
            genres = result.scalars().all()
            
            return [
                {"id": genre.genre_id, "name": genre.name}
                for genre in genres
            ]
            
        except Exception as e:
            print(f"영화 장르 조회 실패: {str(e)}")
            return []
    
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
