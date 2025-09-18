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
from app.database import SessionLocal


class GenreService:

    def __init__(self):
        pass

    def _get_db(self) -> Session:
        """데이터베이스 세션 생성"""
        return SessionLocal()

    async def get_all_genres(self) -> GenreListResponse:
        """모든 장르 조회"""
        db = self._get_db()
        try:
            stmt = select(GenreModel).order_by(GenreModel.name)
            result = db.execute(stmt)
            genres = result.scalars().all()

            genre_list = [self._build_genre_response(genre) for genre in genres]

            return GenreListResponse(genres=genre_list)

        except Exception as e:
            raise Exception(f"장르 목록 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_genre_by_id(self, genre_id: int) -> Optional[Genre]:
        """특정 장르 조회"""
        db = self._get_db()
        try:
            genre_model = self._get_genre_model_by_id(genre_id, db)
            return self._build_genre_response(genre_model) if genre_model else None

        except Exception as e:
            raise Exception(f"장르 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_movies_by_genre(
        self, genre_id: int, skip: int = 0, limit: int = 20
    ) -> GenreMovieListResponse:
        """특정 장르의 영화 목록 조회"""
        db = self._get_db()
        try:
            # 장르 정보 조회
            genre_model = self._get_genre_model_by_id(genre_id, db)
            if not genre_model:
                raise Exception("장르를 찾을 수 없습니다")

            genre = self._build_genre_response(genre_model)

            # 해당 장르의 영화 목록 조회
            movies_stmt = (
                select(MovieModel)
                .join(MovieGenreModel, MovieModel.movie_id == MovieGenreModel.movie_id)
                .where(MovieGenreModel.genre_id == genre_id)
                .order_by(desc(MovieModel.average_rating))
                .offset(skip)
                .limit(limit)
            )

            movies_result = db.execute(movies_stmt)
            movies = movies_result.scalars().all()

            movie_list = [self._build_movie_response(movie) for movie in movies]

            # 총 영화 수
            total = self._get_genre_movie_count(genre_id, db)

            return GenreMovieListResponse(genre=genre, movies=movie_list, total=total)

        except Exception as e:
            raise Exception(f"장르별 영화 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_genre_stats(self) -> GenreStatsResponse:
        """장르별 통계 조회"""
        db = self._get_db()
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

            result = db.execute(stmt)
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
        finally:
            db.close()

    async def get_popular_genres(self, limit: int = 10) -> List[GenreWithMovieCount]:
        """인기 장르 조회 (영화 수 기준)"""
        db = self._get_db()
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

            result = db.execute(stmt)
            popular_data = result.all()

            return [
                GenreWithMovieCount(
                    genre_id=row.genre_id, name=row.name, movie_count=row.movie_count
                )
                for row in popular_data
            ]

        except Exception as e:
            raise Exception(f"인기 장르 조회 실패: {str(e)}")
        finally:
            db.close()

    async def search_genres(self, query: str) -> List[Genre]:
        """장르 검색"""
        db = self._get_db()
        try:
            stmt = (
                select(GenreModel)
                .where(GenreModel.name.ilike(f"%{query}%"))
                .order_by(GenreModel.name)
            )

            result = db.execute(stmt)
            genres = result.scalars().all()

            return [self._build_genre_response(genre) for genre in genres]

        except Exception as e:
            raise Exception(f"장르 검색 실패: {str(e)}")
        finally:
            db.close()

    async def create_genre(self, genre_id: int, name: str) -> Genre:
        """장르 생성"""
        db = self._get_db()
        try:
            # 기존 장르 확인
            existing_genre = self._get_genre_model_by_id(genre_id, db)
            if existing_genre:
                return self._build_genre_response(existing_genre)

            # 새 장르 생성
            new_genre = GenreModel(genre_id=genre_id, name=name)

            db.add(new_genre)
            db.commit()
            db.refresh(new_genre)

            return self._build_genre_response(new_genre)

        except Exception as e:
            db.rollback()
            raise Exception(f"장르 생성 실패: {str(e)}")
        finally:
            db.close()

    async def add_movie_genre(self, movie_id: int, genre_id: int) -> bool:
        """영화-장르 연결 추가"""
        db = self._get_db()
        try:
            # 기존 연결 확인
            if self._is_movie_genre_connected(movie_id, genre_id, db):
                return True  # 이미 연결됨

            # 새 연결 추가
            new_connection = MovieGenreModel(movie_id=movie_id, genre_id=genre_id)

            db.add(new_connection)
            db.commit()

            return True

        except Exception as e:
            db.rollback()
            raise Exception(f"영화-장르 연결 실패: {str(e)}")
        finally:
            db.close()

    # 헬퍼 메서드들 - 세션을 매개변수로 받음
    def _get_genre_model_by_id(self, genre_id: int, db: Session) -> Optional[GenreModel]:
        """장르 모델 조회"""
        stmt = select(GenreModel).where(GenreModel.genre_id == genre_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def _get_genre_movie_count(self, genre_id: int, db: Session) -> int:
        """장르별 영화 수 조회"""
        total_stmt = (
            select(func.count(MovieModel.movie_id))
            .join(MovieGenreModel, MovieModel.movie_id == MovieGenreModel.movie_id)
            .where(MovieGenreModel.genre_id == genre_id)
        )
        total_result = db.execute(total_stmt)
        return total_result.scalar() or 0

    def _is_movie_genre_connected(self, movie_id: int, genre_id: int, db: Session) -> bool:
        """영화-장르 연결 여부 확인"""
        existing_stmt = select(MovieGenreModel).where(
            MovieGenreModel.movie_id == movie_id, MovieGenreModel.genre_id == genre_id
        )
        existing_result = db.execute(existing_stmt)
        return existing_result.scalar_one_or_none() is not None

    def _build_genre_response(self, genre_model: GenreModel) -> Genre:
        """장르 응답 객체 생성"""
        return Genre(
            genre_id=genre_model.genre_id,
            name=genre_model.name,
            created_at=genre_model.created_at,
            updated_at=genre_model.updated_at,
        )

    def _build_movie_response(self, movie_model: MovieModel) -> Movie:
        """영화 응답 객체 생성"""
        return Movie(
            movie_id=movie_model.movie_id,
            title=movie_model.title,
            original_title=movie_model.original_title,
            overview=movie_model.overview,
            release_date=movie_model.release_date,
            runtime=movie_model.runtime,
            poster_url=movie_model.poster_url,
            backdrop_url=movie_model.backdrop_url,
            average_rating=movie_model.average_rating,
            is_adult=movie_model.is_adult,
            trailer_url=movie_model.trailer_url,
            created_at=movie_model.created_at,
            updated_at=movie_model.updated_at,
        )
