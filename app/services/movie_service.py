# app/services/movie_service.py

from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from sqlalchemy.exc import ProgrammingError
from app.models.movie import MovieModel
from app.models.genre import GenreModel
from app.models.movie_genre import MovieGenreModel
from app.models.movie_cast import MovieCastModel
from app.models.person import PersonModel
from app.schemas import Movie
from app.services.tmdb_service import TMDBService
from app.database import get_db
from app.models.movie_like import MovieLikeModel
from app.models.watchlist import WatchlistModel
from app.schemas.movie import MovieLike, Watchlist, WatchlistMovie, MovieWithUserActions

class MovieService:
    
    def __init__(self):
        self.db: Session = next(get_db())
        self.tmdb_service = TMDBService()
    
    async def get_movie_by_movie_id(self, movie_id: int) -> Optional[dict]:
        """DB에서 영화 조회, 없으면 TMDB에서 가져와서 저장"""
        try:
            print(f"DB 조회 시작: {movie_id}")
            
            stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
            result = self.db.execute(stmt)
            movie_model = result.scalar_one_or_none()
            
            if movie_model:
                print(f"DB에서 영화 발견: {movie_model.title}")
                # 기본 영화 정보에 출연진 정보 추가
                movie_dict = Movie.from_orm(movie_model).dict()
                cast_info = await self._get_movie_cast_with_names(movie_id)
                movie_dict.update(cast_info)
                return movie_dict
            
            # DB에 없으면 TMDB에서 가져와서 저장
            print("DB에 영화 없음 - TMDB 조회 시작")
            tmdb_data = await self.tmdb_service.get_movie_details(movie_id, language="ko-KR")
            if tmdb_data:
                saved_movie = await self.save_movie_from_tmdb_data(tmdb_data)
                # 저장 후 출연진 정보 포함해서 반환
                movie_dict = saved_movie.dict()
                cast_info = await self._get_movie_cast_with_names(movie_id)
                movie_dict.update(cast_info)
                return movie_dict
            
            print("TMDB에서도 영화를 찾을 수 없음")
            return None
            
        except Exception as e:
            print(f"DB 조회 실패: {str(e)}")
            raise Exception(f"데이터베이스 조회 실패: {str(e)}")
    
    async def _get_movie_cast_with_names(self, movie_id: int) -> dict:
        """영화의 출연진 정보를 이름과 함께 조회"""
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
            ).select_from(
                MovieCastModel
            ).join( 
                PersonModel, MovieCastModel.person_id == PersonModel.person_id
            ).where(
                MovieCastModel.movie_id == movie_id
            ).order_by(MovieCastModel.cast_order.nulls_last())
            
            result = self.db.execute(stmt)
            cast_data = result.fetchall()
            
            cast_list = []
            crew_list = []
            
            for row in cast_data:
                cast_info = {
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
                    cast_list.append(cast_info)
                else:
                    crew_list.append(cast_info)
            
            return {
                "cast": cast_list,
                "crew": crew_list
            }
            
        except Exception as e:
            print(f"영화 출연진 조회 실패: {str(e)}")
            return {"cast": [], "crew": []}
    
    async def save_movie_from_tmdb_data(self, tmdb_data: dict) -> Movie:
        try:
            movie_id = tmdb_data.get("id")
            print(f"TMDB 데이터 저장 시작 - ID: {movie_id}")
            
            existing_movie = await self._get_movie_from_db_only(movie_id)
            if existing_movie:
                print("이미 DB에 존재함")
                # 기존 영화도 장르와 출연진 정보 업데이트
                await self._save_movie_genres(movie_id, tmdb_data.get("genres", []))
                await self._save_movie_cast_with_person_basic(movie_id, tmdb_data.get("credits", {}))
                return existing_movie
            
            # 1. 영화 정보 저장
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
            
            # 2. 장르 정보 저장
            await self._save_movie_genres(movie_id, tmdb_data.get("genres", []))
            
            # 3. person 기본 정보 + movie_cast 저장
            await self._save_movie_cast_with_person_basic(movie_id, tmdb_data.get("credits", {}))
            
            print(f"DB 저장 완료: {movie_model.movie_id} - {movie_model.title}")
            return Movie.from_orm(movie_model)
            
        except Exception as e:
            self.db.rollback()
            print(f"DB 저장 실패: {str(e)}")
            raise Exception(f"데이터베이스 저장 실패: {str(e)}")
    
    async def _get_movie_from_db_only(self, movie_id: int) -> Optional[Movie]:
        """DB에서만 영화 조회"""
        try:
            stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
            result = self.db.execute(stmt)
            movie_model = result.scalar_one_or_none()
            
            if movie_model:
                return Movie.from_orm(movie_model)
            return None
            
        except Exception as e:
            print(f"DB 조회 실패: {str(e)}")
            return None
    
    async def _save_movie_cast_with_person_basic(self, movie_id: int, credits: dict):
        """person 기본 정보 + movie_cast 저장"""
        try:
            cast_list = credits.get("cast", [])
            crew_list = credits.get("crew", [])
            
            # 출연진 저장
            for cast in cast_list:
                person_id = cast.get("id")
                if not person_id:
                    continue
                
                # person 기본 정보 생성/확인
                await self._ensure_person_basic_info(
                    person_id=person_id,
                    name=cast.get("name", ""),
                    profile_path=cast.get("profile_path"),
                    known_for_department="Acting"
                )
                
                # movie_cast 연결 저장
                await self._ensure_movie_cast_connection(
                    movie_id=movie_id,
                    person_id=person_id,
                    character_name=cast.get("character"),
                    job="Actor",
                    department="Acting",
                    cast_order=cast.get("order", 999),
                    is_main_cast=cast.get("order", 999) < 10
                )
            
            # 주요 스태프 저장
            for crew in crew_list:
                if crew.get("job") in ["Director", "Producer", "Executive Producer", "Screenplay", "Story", "Director of Photography"]:
                    person_id = crew.get("id")
                    if not person_id:
                        continue
                    
                    # person 기본 정보 생성/확인
                    await self._ensure_person_basic_info(
                        person_id=person_id,
                        name=crew.get("name", ""),
                        profile_path=crew.get("profile_path"),
                        known_for_department=crew.get("known_for_department", crew.get("job"))
                    )
                    
                    # movie_cast 연결 저장
                    await self._ensure_movie_cast_connection(
                        movie_id=movie_id,
                        person_id=person_id,
                        character_name=None,
                        job=crew.get("job"),
                        department=crew.get("department"),
                        cast_order=None,
                        is_main_cast=crew.get("job") in ["Director", "Producer"]
                    )
            
            print(f"person 기본정보 + movie_cast 저장 완료: 영화 {movie_id}")
            
        except Exception as e:
            print(f"movie_cast 저장 실패: {str(e)}")
    
    async def _ensure_person_basic_info(self, person_id: int, name: str, profile_path: Optional[str], known_for_department: Optional[str]):
        """인물 기본 정보 생성"""
        try:
            stmt = select(PersonModel).where(PersonModel.person_id == person_id)
            result = self.db.execute(stmt)
            existing_person = result.scalar_one_or_none()
            
            if not existing_person:
                # 기본 정보 저장, 상세 정보는 null
                basic_person = PersonModel(
                    person_id=person_id,
                    name=name,
                    original_name=None,
                    biography=None,
                    birthday=None, 
                    deathday=None, 
                    place_of_birth=None,
                    profile_image_url=self._build_profile_image_url(profile_path),
                    gender=0,      
                    known_for_department=known_for_department,
                    popularity=0,  
                    is_adult=False
                )
                self.db.add(basic_person)
                self.db.commit()
                print(f"인물 기본 정보 생성: {name} (ID: {person_id})")
            else:
                print(f"인물 기본 정보 이미 존재: {existing_person.name} (ID: {person_id})")
        
        except Exception as e:
            self.db.rollback()
            print(f"인물 기본 정보 생성 실패: {str(e)}")
    
    def _build_profile_image_url(self, path: Optional[str]) -> Optional[str]:
        """프로필 이미지 URL 생성"""
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/w500{path}"
    
    async def _ensure_movie_cast_connection(
        self,
        movie_id: int,
        person_id: int,
        character_name: Optional[str],
        job: Optional[str],
        department: Optional[str],
        cast_order: Optional[int],
        is_main_cast: bool
    ):
        """movie_cast 연결 중복 체크 후 저장"""
        try:
            # 중복 체크
            stmt = select(MovieCastModel).where(
                and_(
                    MovieCastModel.movie_id == movie_id,
                    MovieCastModel.person_id == person_id,
                    MovieCastModel.job == job
                )
            )
            result = self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                new_cast = MovieCastModel(
                    movie_id=movie_id,
                    person_id=person_id,
                    character_name=character_name,
                    job=job,
                    department=department,
                    cast_order=cast_order,
                    is_main_cast=is_main_cast
                )
                self.db.add(new_cast)
                self.db.commit()
                print(f"movie_cast 연결 생성: 영화({movie_id}) - 인물({person_id}) - {job}")
            else:
                print(f"movie_cast 이미 존재: 영화({movie_id}) - 인물({person_id}) - {job}")
        
        except Exception as e:
            self.db.rollback()
            print(f"movie_cast 연결 실패: {str(e)}")
    
    # 나머지 메서드들은 동일...
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
                and_(
                    MovieGenreModel.movie_id == movie_id,
                    MovieGenreModel.genre_id == genre_id
                )
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
    
    async def like_movie(self, user_id: int, movie_id: int) -> MovieLike:
        """영화 좋아요"""
        try:
            # 영화 존재 확인
            movie = await self._get_movie_from_db_only(movie_id)
            if not movie:
                raise Exception("존재하지 않는 영화입니다")
            
            # 이미 좋아요 했는지 확인
            if await self._is_movie_liked(user_id, movie_id):
                raise Exception("이미 좋아요한 영화입니다")
            
            # 좋아요 생성
            new_like = MovieLikeModel(
                user_id=user_id,
                movie_id=movie_id
            )
            
            self.db.add(new_like)
            self.db.commit()
            self.db.refresh(new_like)
            
            return MovieLike(
                user_id=new_like.user_id,
                movie_id=new_like.movie_id,
                created_at=new_like.created_at
            )
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"영화 좋아요 실패: {str(e)}")
    
    async def unlike_movie(self, user_id: int, movie_id: int) -> bool:
        """영화 좋아요 취소"""
        try:
            stmt = select(MovieLikeModel).where(
                and_(
                    MovieLikeModel.user_id == user_id,
                    MovieLikeModel.movie_id == movie_id
                )
            )
            result = self.db.execute(stmt)
            like = result.scalar_one_or_none()
            
            if not like:
                raise Exception("좋아요 기록을 찾을 수 없습니다")
            
            self.db.delete(like)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"좋아요 취소 실패: {str(e)}")
    
    async def add_to_watchlist(self, user_id: int, movie_id: int) -> Watchlist:
        """왓치리스트에 영화 추가"""
        try:
            # 영화 존재 확인
            movie = await self._get_movie_from_db_only(movie_id)
            if not movie:
                raise Exception("존재하지 않는 영화입니다")
            
            # 이미 왓치리스트에 있는지 확인
            if await self._is_in_watchlist(user_id, movie_id):
                raise Exception("이미 왓치리스트에 있는 영화입니다")
            
            # 왓치리스트 추가
            new_watchlist = WatchlistModel(
                user_id=user_id,
                movie_id=movie_id
            )
            
            self.db.add(new_watchlist)
            self.db.commit()
            self.db.refresh(new_watchlist)
            
            return Watchlist(
                user_id=new_watchlist.user_id,
                movie_id=new_watchlist.movie_id,
                created_at=new_watchlist.created_at
            )
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"왓치리스트 추가 실패: {str(e)}")
    
    async def remove_from_watchlist(self, user_id: int, movie_id: int) -> bool:
        """왓치리스트에서 영화 제거"""
        try:
            stmt = select(WatchlistModel).where(
                and_(
                    WatchlistModel.user_id == user_id,
                    WatchlistModel.movie_id == movie_id
                )
            )
            result = self.db.execute(stmt)
            watchlist = result.scalar_one_or_none()
            
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
                MovieModel.movie_id,
                MovieModel.title,
                MovieModel.poster_url,
                MovieModel.release_date,
                MovieModel.average_rating,
                WatchlistModel.created_at
            ).join(
                WatchlistModel, MovieModel.movie_id == WatchlistModel.movie_id
            ).where(
                WatchlistModel.user_id == user_id
            ).order_by(
                WatchlistModel.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = self.db.execute(stmt)
            watchlist_movies = []
            
            for row in result:
                watchlist_movies.append(WatchlistMovie(
                    movie_id=row.movie_id,
                    title=row.title,
                    poster_url=row.poster_url,
                    release_date=row.release_date,
                    average_rating=row.average_rating,
                    added_at=row.created_at
                ))
            
            return watchlist_movies
            
        except Exception as e:
            raise Exception(f"왓치리스트 조회 실패: {str(e)}")
    
    async def get_user_liked_movies(self, user_id: int, limit: int = 20, offset: int = 0) -> list[WatchlistMovie]:
        """사용자가 좋아요한 영화 목록"""
        try:
            stmt = select(
                MovieModel.movie_id,
                MovieModel.title,
                MovieModel.poster_url,
                MovieModel.release_date,
                MovieModel.average_rating,
                MovieLikeModel.created_at
            ).join(
                MovieLikeModel, MovieModel.movie_id == MovieLikeModel.movie_id
            ).where(
                MovieLikeModel.user_id == user_id
            ).order_by(
                MovieLikeModel.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = self.db.execute(stmt)
            liked_movies = []
            
            for row in result:
                liked_movies.append(WatchlistMovie(
                    movie_id=row.movie_id,
                    title=row.title,
                    poster_url=row.poster_url,
                    release_date=row.release_date,
                    average_rating=row.average_rating,
                    added_at=row.created_at
                ))
            
            return liked_movies
            
        except Exception as e:
            raise Exception(f"좋아요 영화 조회 실패: {str(e)}")
    
    async def get_movie_with_user_actions(self, movie_id: int, user_id: Optional[int] = None) -> Optional[dict]:
        """사용자 액션 정보가 포함된 영화 상세 정보"""
        try:
            # 기본 영화 정보 조회
            movie_dict = await self.get_movie_by_movie_id(movie_id)
            if not movie_dict:
                return None
            
            # 사용자 액션 정보 추가
            if user_id:
                is_liked = await self._is_movie_liked(user_id, movie_id)
                is_in_watchlist = await self._is_in_watchlist(user_id, movie_id)
                movie_dict["is_liked"] = is_liked
                movie_dict["is_in_watchlist"] = is_in_watchlist
            else:
                movie_dict["is_liked"] = False
                movie_dict["is_in_watchlist"] = False
            
            # 총 좋아요 수 추가
            likes_count = await self._get_movie_likes_count(movie_id)
            movie_dict["likes_count"] = likes_count
            
            return movie_dict
            
        except Exception as e:
            raise Exception(f"영화 상세 정보 조회 실패: {str(e)}")
    
    async def _is_movie_liked(self, user_id: int, movie_id: int) -> bool:
        """사용자가 영화를 좋아요했는지 확인"""
        try:
            stmt = select(MovieLikeModel).where(
                and_(
                    MovieLikeModel.user_id == user_id,
                    MovieLikeModel.movie_id == movie_id
                )
            )
            result = self.db.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception:
            return False
    
    async def _is_in_watchlist(self, user_id: int, movie_id: int) -> bool:
        """영화가 왓치리스트에 있는지 확인"""
        try:
            stmt = select(WatchlistModel).where(
                and_(
                    WatchlistModel.user_id == user_id,
                    WatchlistModel.movie_id == movie_id
                )
            )
            result = self.db.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception:
            return False
    
    async def _get_movie_likes_count(self, movie_id: int) -> int:
        """영화의 총 좋아요 수"""
        try:
            stmt = select(func.count(MovieLikeModel.user_id)).where(
                MovieLikeModel.movie_id == movie_id
            )
            result = self.db.execute(stmt)
            return result.scalar() or 0
        except Exception:
            return 0
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
