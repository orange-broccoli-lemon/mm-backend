# app/services/genre_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from app.models.genre import GenreModel
from app.models.movie import MovieModel
from app.models.movie_genre import MovieGenreModel
from app.schemas.genre import (
    Genre,
    GenreWithMovieCount,
    GenreListResponse,
    GenreMovieListResponse,
    GenreStatsResponse,
)
from app.schemas.movie import Movie
from app.database import get_db


class GenreService:

    def __init__(self):
        self.db: Session = next(get_db())

    async def get_all_genres(self) -> GenreListResponse:
        """모든 장르 조회"""
        try:
            stmt = select(GenreModel).order_by(GenreModel.name)
            result = self.db.execute(stmt)
            genres = result.scalars().all()

            genre_list = [
                Genre(
                    genre_id=genre.genre_id,
                    name=genre.name,
                    created_at=genre.created_at,
                    updated_at=genre.updated_at,
                )
                for genre in genres
            ]

            return GenreListResponse(genres=genre_list)

        except Exception as e:
            raise Exception(f"장르 목록 조회 실패: {str(e)}")

    async def get_genre_by_id(self, genre_id: int) -> Optional[Genre]:
        """특정 장르 조회"""
        try:
            stmt = select(GenreModel).where(GenreModel.genre_id == genre_id)
            result = self.db.execute(stmt)
            genre_model = result.scalar_one_or_none()

            if not genre_model:
                return None

            return Genre(
                genre_id=genre_model.genre_id,
                name=genre_model.name,
                created_at=genre_model.created_at,
                updated_at=genre_model.updated_at,
            )

        except Exception as e:
            raise Exception(f"장르 조회 실패: {str(e)}")

    async def get_movies_by_genre(
        self, genre_id: int, skip: int = 0, limit: int = 20
    ) -> GenreMovieListResponse:
        """특정 장르의 영화 목록 조회"""
        try:
            # 장르 정보 조회
            genre = await self.get_genre_by_id(genre_id)
            if not genre:
                raise Exception("장르를 찾을 수 없습니다")

            # 해당 장르의 영화 목록 조회
            stmt = (
                select(MovieModel)
                .join(MovieGenreModel, MovieModel.movie_id == MovieGenreModel.movie_id)
                .where(MovieGenreModel.genre_id == genre_id)
                .order_by(desc(MovieModel.average_rating))
                .offset(skip)
                .limit(limit)
            )

            result = self.db.execute(stmt)
            movies = result.scalars().all()

            movie_list = [
                Movie(
                    movie_id=movie.movie_id,
                    title=movie.title,
                    original_title=movie.original_title,
                    overview=movie.overview,
                    release_date=movie.release_date,
                    runtime=movie.runtime,
                    poster_url=movie.poster_url,
                    backdrop_url=movie.backdrop_url,
                    average_rating=movie.average_rating,
                    is_adult=movie.is_adult,
                    trailer_url=movie.trailer_url,
                    created_at=movie.created_at,
                    updated_at=movie.updated_at,
                )
                for movie in movies
            ]

            # 총 영화 수
            total_stmt = (
                select(func.count(MovieModel.movie_id))
                .join(MovieGenreModel, MovieModel.movie_id == MovieGenreModel.movie_id)
                .where(MovieGenreModel.genre_id == genre_id)
            )

            total_result = self.db.execute(total_stmt)
            total = total_result.scalar() or 0

            return GenreMovieListResponse(genre=genre, movies=movie_list, total=total)

        except Exception as e:
            raise Exception(f"장르별 영화 조회 실패: {str(e)}")

    async def get_genre_stats(self) -> GenreStatsResponse:
        """장르별 통계 조회"""
        try:
            # 장르별 영화 수 조회
            stmt = (
                select(
                    GenreModel.genre_id,
                    GenreModel.name,
                    func.count(MovieGenreModel.movie_id).label("movie_count"),
                )
                .outerjoin(MovieGenreModel, GenreModel.genre_id == MovieGenreModel.genre_id)
                .group_by(GenreModel.genre_id, GenreModel.name)
                .order_by(desc(func.count(MovieGenreModel.movie_id)))
            )

            result = self.db.execute(stmt)
            stats_data = result.all()

            genre_stats = [
                GenreWithMovieCount(
                    genre_id=row.genre_id, name=row.name, movie_count=row.movie_count or 0
                )
                for row in stats_data
            ]

            return GenreStatsResponse(genres=genre_stats, total_genres=len(genre_stats))

        except Exception as e:
            raise Exception(f"장르 통계 조회 실패: {str(e)}")

    async def get_popular_genres(self, limit: int = 10) -> List[GenreWithMovieCount]:
        """인기 장르 조회 (영화 수 기준)"""
        try:
            stmt = (
                select(
                    GenreModel.genre_id,
                    GenreModel.name,
                    func.count(MovieGenreModel.movie_id).label("movie_count"),
                )
                .join(MovieGenreModel, GenreModel.genre_id == MovieGenreModel.genre_id)
                .group_by(GenreModel.genre_id, GenreModel.name)
                .order_by(desc(func.count(MovieGenreModel.movie_id)))
                .limit(limit)
            )

            result = self.db.execute(stmt)
            popular_data = result.all()

            return [
                GenreWithMovieCount(
                    genre_id=row.genre_id, name=row.name, movie_count=row.movie_count
                )
                for row in popular_data
            ]

        except Exception as e:
            raise Exception(f"인기 장르 조회 실패: {str(e)}")

    async def search_genres(self, query: str) -> List[Genre]:
        """장르 검색"""
        try:
            stmt = (
                select(GenreModel)
                .where(GenreModel.name.ilike(f"%{query}%"))
                .order_by(GenreModel.name)
            )

            result = self.db.execute(stmt)
            genres = result.scalars().all()

            return [
                Genre(
                    genre_id=genre.genre_id,
                    name=genre.name,
                    created_at=genre.created_at,
                    updated_at=genre.updated_at,
                )
                for genre in genres
            ]

        except Exception as e:
            raise Exception(f"장르 검색 실패: {str(e)}")

    async def create_genre(self, genre_id: int, name: str) -> Genre:
        """장르 생성"""
        try:
            # 기존 장르 확인
            existing_genre = await self.get_genre_by_id(genre_id)
            if existing_genre:
                return existing_genre

            # 새 장르 생성
            new_genre = GenreModel(genre_id=genre_id, name=name)

            self.db.add(new_genre)
            self.db.commit()
            self.db.refresh(new_genre)

            return Genre(
                genre_id=new_genre.genre_id,
                name=new_genre.name,
                created_at=new_genre.created_at,
                updated_at=new_genre.updated_at,
            )

        except Exception as e:
            self.db.rollback()
            raise Exception(f"장르 생성 실패: {str(e)}")

    async def add_movie_genre(self, movie_id: int, genre_id: int) -> bool:
        """영화-장르 연결 추가"""
        try:
            # 기존 연결 확인
            existing_stmt = select(MovieGenreModel).where(
                MovieGenreModel.movie_id == movie_id, MovieGenreModel.genre_id == genre_id
            )
            existing_result = self.db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                return True  # 이미 연결됨

            # 새 연결 추가
            new_connection = MovieGenreModel(movie_id=movie_id, genre_id=genre_id)

            self.db.add(new_connection)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            raise Exception(f"영화-장르 연결 실패: {str(e)}")

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()
