# app/services/movie_service.py

from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from app.models.movie import MovieModel
from app.models.genre import GenreModel
from app.models.movie_genre import MovieGenreModel
from app.models.movie_cast import MovieCastModel
from app.models.person import PersonModel
from app.models.movie_like import MovieLikeModel
from app.models.watchlist import WatchlistModel
from app.schemas.movie import Movie, MovieLike, Watchlist, WatchlistMovie
from app.services.tmdb_service import TMDBService
from app.database import get_db


class MovieService:
    
    def __init__(self):
        self.db: Session = next(get_db())
        self.tmdb_service = TMDBService()
    
    async def get_movie_detail(self, movie_id: int, user_id: Optional[int] = None) -> Optional[dict]:
        """영화 상세 정보 조회"""
        try:
            print(f"영화 상세 조회: {movie_id}")
            
            # 1. DB에서 영화 조회
            stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
            result = self.db.execute(stmt)
            movie_model = result.scalar_one_or_none()
            
            # 2. DB에 없으면 TMDB에서 가져와서 저장
            if not movie_model:
                print("DB에 영화 없음 - TMDB에서 저장")
                movie_model = await self._fetch_and_save_from_tmdb(movie_id)
                if not movie_model:
                    return None
            
            # 3. 영화 기본 정보 구성
            movie_dict = {
                "movie_id": movie_model.movie_id,
                "title": movie_model.title,
                "original_title": movie_model.original_title,
                "overview": movie_model.overview,
                "release_date": movie_model.release_date,
                "runtime": movie_model.runtime,
                "poster_url": movie_model.poster_url,
                "backdrop_url": movie_model.backdrop_url,
                "average_rating": movie_model.average_rating,
                "is_adult": movie_model.is_adult,
                "trailer_url": movie_model.trailer_url,
                "created_at": movie_model.created_at,
                "updated_at": movie_model.updated_at
            }
            
            # 4. 출연진/스태프 정보 추가
            cast_info = await self._get_movie_cast_info(movie_id)
            movie_dict.update(cast_info)
            
            # 5. 사용자 액션 정보 추가
            if user_id:
                movie_dict["is_liked"] = await self._is_movie_liked(user_id, movie_id)
                movie_dict["is_in_watchlist"] = await self._is_in_watchlist(user_id, movie_id)
            else:
                movie_dict["is_liked"] = False
                movie_dict["is_in_watchlist"] = False
            
            # 6. 좋아요 수 추가
            movie_dict["likes_count"] = await self._get_movie_likes_count(movie_id)
            
            return movie_dict
            
        except Exception as e:
            print(f"영화 상세 조회 실패: {str(e)}")
            raise Exception(f"영화 상세 조회 실패: {str(e)}")
    
    async def _fetch_and_save_from_tmdb(self, movie_id: int) -> Optional[MovieModel]:
        """TMDB에서 영화 정보를 가져와서 DB에 저장"""
        try:
            # TMDB에서 영화 상세 정보 조회
            tmdb_data = await self.tmdb_service.get_movie_details(movie_id, language="ko-KR")
            if not tmdb_data:
                return None
            
            # 영화 정보 저장
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
            
            # 출연진/스태프 정보 저장
            await self._save_movie_cast(movie_id, tmdb_data.get("credits", {}))
            
            print(f"TMDB에서 영화 저장 완료: {movie_model.title}")
            return movie_model
            
        except Exception as e:
            self.db.rollback()
            print(f"TMDB 영화 저장 실패: {str(e)}")
            return None
    
    async def _get_movie_cast_info(self, movie_id: int) -> dict:
        """영화의 출연진/감독 조회 (department 기준 분류, 배우 10/감독 1 응답)"""
        try:
            stmt = select(
                MovieCastModel.person_id,
                PersonModel.name,
                PersonModel.profile_image_url,
                MovieCastModel.character_name,
                MovieCastModel.job,
                MovieCastModel.department,
                MovieCastModel.cast_order,
                MovieCastModel.is_main_cast
            ).join(
                PersonModel, MovieCastModel.person_id == PersonModel.person_id
            ).where(
                MovieCastModel.movie_id == movie_id
            ).order_by(
                MovieCastModel.cast_order.nulls_last()
            )

            rows = self.db.execute(stmt).fetchall()

            cast_acting = []
            directors = []

            for row in rows:
                item = {
                    "person_id": row.person_id,
                    "name": row.name,
                    "profile_image_url": row.profile_image_url,
                    "character_name": row.character_name,
                    "job": row.job,
                    "department": row.department,
                    "cast_order": row.cast_order,
                    "is_main_cast": row.is_main_cast
                }

                if row.department == "Acting":
                    cast_acting.append(item)

                elif row.department == "Directing" and row.job == "Director":
                    directors.append(item)

            return {
                "cast": cast_acting[:10],
                "crew": directors[:1],
                "cast_total": len(cast_acting),
                "directors_total": len(directors)
            }

        except Exception as e:
            print(f"출연진 조회 실패: {str(e)}")
            return {"cast": [], "crew": [], "cast_total": 0, "directors_total": 0}

    async def _save_movie_cast(self, movie_id: int, credits: dict):
        """TMDB cast 저장"""
        try:
            for cast in credits.get("cast", []):
                person_id = cast.get("id")
                if not person_id:
                    continue

                name = cast.get("name", "")
                profile_path = cast.get("profile_path")
                character = cast.get("character")
                order = cast.get("order", 999)
                job = cast.get("job") or "Actor"
                department = cast.get("department") or "Acting"

                await self._ensure_person_exists(
                    person_id=person_id,
                    name=name,
                    profile_path=profile_path
                )

                await self._save_cast_connection(
                    movie_id=movie_id,
                    person_id=person_id,
                    character=character,
                    job=job,
                    department=department,
                    order=order
                )

            director = next((c for c in credits.get("crew", []) if c.get("job") == "Director"), None)

            if director:
                director_id = director.get("id")
                if director_id:
                    await self._ensure_person_exists(
                        person_id=director_id,
                        name=director.get("name", ""),
                        profile_path=director.get("profile_path")
                    )
                    await self._save_cast_connection(
                        movie_id=movie_id,
                        person_id=director_id,
                        character=None,
                        job="Director",
                        department=director.get("department") or "Directing",
                        order=None
                    )

        except Exception as e:
            print(f"출연진/감독 저장 실패: {str(e)}")
    
    async def _ensure_person_exists(self, person_id: int, name: str, profile_path: Optional[str]):
        """인물 정보가 DB에 없으면 생성"""
        try:
            stmt = select(PersonModel).where(PersonModel.person_id == person_id)
            result = self.db.execute(stmt)
            
            if not result.scalar_one_or_none():
                person = PersonModel(
                    person_id=person_id,
                    name=name,
                    profile_image_url=self._build_profile_image_url(profile_path),
                    popularity=0,
                    gender=0,
                    is_adult=False
                )
                self.db.add(person)
                self.db.commit()
        
        except Exception as e:
            self.db.rollback()
            print(f"인물 생성 실패: {str(e)}")
    
    async def _save_cast_connection(self, movie_id: int, person_id: int, 
                                  character: Optional[str], job: str, 
                                  department: str, order: Optional[int]):
        """movie_cast 연결 저장"""
        try:
            # 중복 체크
            stmt = select(MovieCastModel).where(
                and_(
                    MovieCastModel.movie_id == movie_id,
                    MovieCastModel.person_id == person_id,
                    MovieCastModel.job == job
                )
            )
            
            if not self.db.execute(stmt).scalar_one_or_none():
                cast = MovieCastModel(
                    movie_id=movie_id,
                    person_id=person_id,
                    character_name=character,
                    job=job,
                    department=department,
                    cast_order=order,
                    is_main_cast=(order or 999) < 10 if department == "Acting" else job in ["Director", "Producer"]
                )
                self.db.add(cast)
                self.db.commit()
        
        except Exception as e:
            self.db.rollback()
            print(f"출연진 연결 실패: {str(e)}")
    
    async def _save_movie_genres(self, movie_id: int, genres: List[dict]):
        """영화 장르 저장"""
        try:
            for genre_data in genres:
                genre_id = genre_data.get("id")
                genre_name = genre_data.get("name")
                
                if genre_id and genre_name:
                    # 장르 생성
                    stmt = select(GenreModel).where(GenreModel.genre_id == genre_id)
                    if not self.db.execute(stmt).scalar_one_or_none():
                        genre = GenreModel(genre_id=genre_id, name=genre_name)
                        self.db.add(genre)
                        self.db.commit()
                    
                    # 영화-장르 연결
                    stmt = select(MovieGenreModel).where(
                        and_(
                            MovieGenreModel.movie_id == movie_id,
                            MovieGenreModel.genre_id == genre_id
                        )
                    )
                    if not self.db.execute(stmt).scalar_one_or_none():
                        connection = MovieGenreModel(movie_id=movie_id, genre_id=genre_id)
                        self.db.add(connection)
                        self.db.commit()
        
        except Exception as e:
            print(f"장르 저장 실패: {str(e)}")
    
    # 좋아요/왓치리스트 기능
    async def like_movie(self, user_id: int, movie_id: int) -> MovieLike:
        """영화 좋아요"""
        try:
            if await self._is_movie_liked(user_id, movie_id):
                raise Exception("이미 좋아요한 영화입니다")
            
            like = MovieLikeModel(user_id=user_id, movie_id=movie_id)
            self.db.add(like)
            self.db.commit()
            self.db.refresh(like)
            
            return MovieLike(
                user_id=like.user_id,
                movie_id=like.movie_id,
                created_at=like.created_at
            )
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"영화 좋아요 실패: {str(e)}")
    
    async def unlike_movie(self, user_id: int, movie_id: int) -> bool:
        """영화 좋아요 취소"""
        try:
            stmt = select(MovieLikeModel).where(
                and_(MovieLikeModel.user_id == user_id, MovieLikeModel.movie_id == movie_id)
            )
            like = self.db.execute(stmt).scalar_one_or_none()
            
            if not like:
                raise Exception("좋아요 기록을 찾을 수 없습니다")
            
            self.db.delete(like)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"좋아요 취소 실패: {str(e)}")
    
    async def add_to_watchlist(self, user_id: int, movie_id: int) -> Watchlist:
        """왓치리스트에 추가"""
        try:
            if await self._is_in_watchlist(user_id, movie_id):
                raise Exception("이미 왓치리스트에 있는 영화입니다")
            
            watchlist = WatchlistModel(user_id=user_id, movie_id=movie_id)
            self.db.add(watchlist)
            self.db.commit()
            self.db.refresh(watchlist)
            
            return Watchlist(
                user_id=watchlist.user_id,
                movie_id=watchlist.movie_id,
                created_at=watchlist.created_at
            )
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"왓치리스트 추가 실패: {str(e)}")
    
    async def remove_from_watchlist(self, user_id: int, movie_id: int) -> bool:
        """왓치리스트에서 제거"""
        try:
            stmt = select(WatchlistModel).where(
                and_(WatchlistModel.user_id == user_id, WatchlistModel.movie_id == movie_id)
            )
            watchlist = self.db.execute(stmt).scalar_one_or_none()
            
            if not watchlist:
                raise Exception("왓치리스트에서 영화를 찾을 수 없습니다")
            
            self.db.delete(watchlist)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"왓치리스트 제거 실패: {str(e)}")
    
    async def get_user_watchlist(self, user_id: int, limit: int = 20, offset: int = 0) -> list[WatchlistMovie]:
        """사용자 왓치리스트 조회"""
        try:
            stmt = select(
                MovieModel.movie_id, MovieModel.title, MovieModel.poster_url,
                MovieModel.release_date, MovieModel.average_rating, WatchlistModel.created_at
            ).join(
                WatchlistModel, MovieModel.movie_id == WatchlistModel.movie_id
            ).where(
                WatchlistModel.user_id == user_id
            ).order_by(WatchlistModel.created_at.desc()).limit(limit).offset(offset)
            
            result = self.db.execute(stmt)
            return [
                WatchlistMovie(
                    movie_id=row.movie_id, title=row.title, poster_url=row.poster_url,
                    release_date=row.release_date, average_rating=row.average_rating,
                    added_at=row.created_at
                ) for row in result
            ]
            
        except Exception as e:
            raise Exception(f"왓치리스트 조회 실패: {str(e)}")
    
    async def get_user_liked_movies(self, user_id: int, limit: int = 20, offset: int = 0) -> list[WatchlistMovie]:
        """사용자가 좋아요한 영화"""
        try:
            stmt = select(
                MovieModel.movie_id, MovieModel.title, MovieModel.poster_url,
                MovieModel.release_date, MovieModel.average_rating, MovieLikeModel.created_at
            ).join(
                MovieLikeModel, MovieModel.movie_id == MovieLikeModel.movie_id
            ).where(
                MovieLikeModel.user_id == user_id
            ).order_by(MovieLikeModel.created_at.desc()).limit(limit).offset(offset)
            
            result = self.db.execute(stmt)
            return [
                WatchlistMovie(
                    movie_id=row.movie_id, title=row.title, poster_url=row.poster_url,
                    release_date=row.release_date, average_rating=row.average_rating,
                    added_at=row.created_at
                ) for row in result
            ]
            
        except Exception as e:
            raise Exception(f"좋아요 영화 조회 실패: {str(e)}")
    
    async def get_all_movies(self, skip: int = 0, limit: int = 100) -> List[Movie]:
        """개발용 - 전체 영화 조회"""
        try:
            stmt = select(MovieModel).offset(skip).limit(limit).order_by(MovieModel.created_at.desc())
            result = self.db.execute(stmt)
            return [Movie.from_orm(movie) for movie in result.scalars()]
            
        except Exception as e:
            raise Exception(f"영화 목록 조회 실패: {str(e)}")
    
    # 유틸리티 메서드들
    async def _is_movie_liked(self, user_id: int, movie_id: int) -> bool:
        """좋아요 여부 확인"""
        try:
            stmt = select(MovieLikeModel).where(
                and_(MovieLikeModel.user_id == user_id, MovieLikeModel.movie_id == movie_id)
            )
            return self.db.execute(stmt).scalar_one_or_none() is not None
        except:
            return False
    
    async def _is_in_watchlist(self, user_id: int, movie_id: int) -> bool:
        """왓치리스트 포함 여부 확인"""
        try:
            stmt = select(WatchlistModel).where(
                and_(WatchlistModel.user_id == user_id, WatchlistModel.movie_id == movie_id)
            )
            return self.db.execute(stmt).scalar_one_or_none() is not None
        except:
            return False
    
    async def _get_movie_likes_count(self, movie_id: int) -> int:
        """영화 좋아요 수"""
        try:
            stmt = select(func.count(MovieLikeModel.user_id)).where(
                MovieLikeModel.movie_id == movie_id
            )
            return self.db.execute(stmt).scalar() or 0
        except:
            return 0
    
    def _parse_date(self, date_str: Optional[str]):
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            return None
    
    def _build_image_url(self, path: Optional[str], size: str) -> Optional[str]:
        return f"https://image.tmdb.org/t/p/{size}{path}" if path else None
    
    def _build_profile_image_url(self, path: Optional[str]) -> Optional[str]:
        return f"https://image.tmdb.org/t/p/w500{path}" if path else None
    
    def _extract_trailer_url(self, movie_data: dict) -> Optional[str]:
        videos = movie_data.get("videos", {}).get("results", [])
        for video in videos:
            if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                return f"https://www.youtube.com/watch?v={video.get('key')}"
        return None
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
