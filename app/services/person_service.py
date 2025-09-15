# app/services/person_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc, or_
from app.models.person import PersonModel
from app.models.person_follow import PersonFollowModel
from app.models.movie_cast import MovieCastModel
from app.models.movie import MovieModel
from app.schemas.person import (
    Person, PersonFollow, PersonStats, PersonCreditsResponse, 
    MovieCredit, PersonFeedItem, PersonFeedResponse
)
from app.services.tmdb_service import TMDBService
from app.database import get_db

class PersonService:
    
    def __init__(self):
        self.db: Session = next(get_db())
        self.tmdb_service = TMDBService()
    
    async def get_person_by_id(self, person_id: int, current_user_id: Optional[int] = None) -> Optional[Person]:
        """인물 상세 정보 조회 - 기본 정보가 있으면 상세 정보로 업데이트"""
        try:
            # 1. DB에서 먼저 조회
            stmt = select(PersonModel).where(PersonModel.person_id == person_id)
            result = self.db.execute(stmt)
            person_model = result.scalar_one_or_none()
            
            # 2. DB에 없거나 상세 정보가 없으면 TMDB에서 업데이트
            if not person_model or not person_model.biography:
                print(f"인물 상세 정보 업데이트 필요: {person_id}")
                person_model = await self._update_person_details_from_tmdb(person_id, person_model)
                if not person_model:
                    return None
            
            # 3. Person 스키마로 변환
            is_following = False
            if current_user_id:
                is_following = await self._is_following_person(current_user_id, person_id)
            
            followers_count = await self._get_person_followers_count(person_id)
            
            return Person(
                person_id=person_model.person_id,
                name=person_model.name,
                original_name=person_model.original_name,
                biography=person_model.biography,
                birthday=person_model.birthday,
                deathday=person_model.deathday,
                place_of_birth=person_model.place_of_birth,
                profile_image_url=person_model.profile_image_url,
                gender=person_model.gender,
                known_for_department=person_model.known_for_department,
                popularity=person_model.popularity,
                is_adult=person_model.is_adult,
                is_following=is_following,
                followers_count=followers_count,
                created_at=person_model.created_at,
                updated_at=person_model.updated_at
            )
            
        except Exception as e:
            raise Exception(f"인물 조회 실패: {str(e)}")
    
    async def _update_person_details_from_tmdb(self, person_id: int, existing_person: Optional[PersonModel]) -> Optional[PersonModel]:
        """TMDB에서 인물 상세 정보로 업데이트 + 영화 기본 정보와 movie_cast 저장"""
        try:
            # 1. TMDB에서 인물 상세 정보 조회
            tmdb_data = await self.tmdb_service.get_person_details(person_id)
            if not tmdb_data:
                print(f"TMDB에서 인물을 찾을 수 없음: {person_id}")
                return existing_person
            
            if existing_person:
                # 2-1. 기존 기본 정보를 상세 정보로 업데이트
                existing_person.name = tmdb_data.get("name", existing_person.name)
                existing_person.original_name = tmdb_data.get("also_known_as", [None])[0] if tmdb_data.get("also_known_as") else None
                existing_person.biography = tmdb_data.get("biography")
                existing_person.birthday = self._parse_date(tmdb_data.get("birthday"))
                existing_person.deathday = self._parse_date(tmdb_data.get("deathday"))
                existing_person.place_of_birth = tmdb_data.get("place_of_birth")
                existing_person.gender = tmdb_data.get("gender", 0)
                existing_person.popularity = int(tmdb_data.get("popularity", 0))
                existing_person.is_adult = tmdb_data.get("adult", False)
                # 더 좋은 프로필 이미지로 업데이트
                if tmdb_data.get("profile_path"):
                    existing_person.profile_image_url = self._build_profile_image_url(tmdb_data.get("profile_path"))
                
                self.db.commit()
                self.db.refresh(existing_person)
                print(f"인물 상세 정보 업데이트: {existing_person.name} (ID: {person_id})")
                person_model = existing_person
            else:
                # 2-2. 새로 생성 (기본 정보가 없는 경우)
                person_model = PersonModel(
                    person_id=tmdb_data.get("id"),
                    name=tmdb_data.get("name", ""),
                    original_name=tmdb_data.get("also_known_as", [None])[0] if tmdb_data.get("also_known_as") else None,
                    biography=tmdb_data.get("biography"),
                    birthday=self._parse_date(tmdb_data.get("birthday")),
                    deathday=self._parse_date(tmdb_data.get("deathday")),
                    place_of_birth=tmdb_data.get("place_of_birth"),
                    profile_image_url=self._build_profile_image_url(tmdb_data.get("profile_path")),
                    gender=tmdb_data.get("gender", 0),
                    known_for_department=tmdb_data.get("known_for_department"),
                    popularity=int(tmdb_data.get("popularity", 0)),
                    is_adult=tmdb_data.get("adult", False)
                )
                
                self.db.add(person_model)
                self.db.commit()
                self.db.refresh(person_model)
                print(f"인물 상세 정보 새로 생성: {person_model.name} (ID: {person_id})")
            
            # 3. 영화 기본 정보 + movie_cast 저장
            await self._save_person_movie_cast_with_movie_basic(person_id)
            
            return person_model
            
        except Exception as e:
            self.db.rollback()
            print(f"TMDB 인물 상세 정보 업데이트 실패: {str(e)}")
            return existing_person
    
    async def _save_person_movie_cast_with_movie_basic(self, person_id: int):
        """영화 기본 정보 + movie_cast 저장"""
        try:
            # TMDB에서 인물의 영화 출연 정보 조회
            credits_data = await self.tmdb_service.get_person_movie_credits(person_id)
            if not credits_data:
                return
            
            # 출연 작품 저장 (상위 30편까지)
            cast_credits = credits_data.get("cast", [])
            for cast in cast_credits[:30]:
                movie_id = cast.get("id")
                if not movie_id:
                    continue
                
                # 영화 기본 정보 저장
                await self._ensure_movie_basic_info(
                    movie_id=movie_id,
                    title=cast.get("title", ""),
                    poster_path=cast.get("poster_path"),
                    release_date=cast.get("release_date")
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
            
            # 스태프 참여 작품 저장
            crew_credits = credits_data.get("crew", [])
            for crew in crew_credits:
                movie_id = crew.get("id")
                if not movie_id:
                    continue
                
                # 주요 역할만 저장
                if crew.get("job") in ["Director", "Producer", "Executive Producer", "Screenplay", "Story", "Director of Photography"]:
                    # 영화 기본 정보 저장
                    await self._ensure_movie_basic_info(
                        movie_id=movie_id,
                        title=crew.get("title", ""),
                        poster_path=crew.get("poster_path"),
                        release_date=crew.get("release_date")
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
            
            print(f"영화 기본정보 + movie_cast 저장 완료: 인물 {person_id}")
            
        except Exception as e:
            print(f"인물 movie_cast 저장 실패: {str(e)}")
    
    async def _ensure_movie_basic_info(self, movie_id: int, title: str, poster_path: Optional[str], release_date: Optional[str]):
        """영화 기본 정보만 저장 (이미 있으면 업데이트 안함)"""
        try:
            stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
            result = self.db.execute(stmt)
            existing_movie = result.scalar_one_or_none()
            
            if not existing_movie:
                from decimal import Decimal
                
                basic_movie = MovieModel(
                    movie_id=movie_id,
                    title=title,
                    original_title=None,
                    overview=None,  # 상세 정보는 영화 상세 조회시에만
                    release_date=self._parse_date(release_date),
                    runtime=None,
                    poster_url=self._build_image_url(poster_path, "w500"),
                    backdrop_url=None,
                    average_rating=Decimal("0.0"),
                    is_adult=False,
                    trailer_url=None
                )
                self.db.add(basic_movie)
                self.db.commit()
                print(f"영화 기본 정보 저장: {title} (ID: {movie_id})")
            else:
                print(f"영화 기본 정보 이미 존재: {existing_movie.title} (ID: {movie_id})")
        
        except Exception as e:
            self.db.rollback()
            print(f"영화 기본 정보 저장 실패: {str(e)}")
    
    def _build_image_url(self, path: Optional[str], size: str) -> Optional[str]:
        """이미지 URL 생성"""
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/{size}{path}"
    
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
    
    async def get_person_credits(self, person_id: int) -> PersonCreditsResponse:
        """인물의 영화 출연/참여 작품 조회 (영화 테이블과 조인)"""
        try:
            person = await self.get_person_by_id(person_id)
            if not person:
                raise Exception("존재하지 않는 인물입니다")
            
            # 출연 작품 조회 (movie 테이블과 조인)
            acting_stmt = select(
                MovieCastModel.movie_id,
                MovieModel.title,
                MovieModel.poster_url,
                MovieModel.release_date,
                MovieCastModel.character_name,
                MovieCastModel.job,
                MovieCastModel.department,
                MovieCastModel.is_main_cast
            ).select_from(
                MovieCastModel
            ).outerjoin(  # LEFT JOIN - movie 기본 정보가 없어도 표시
                MovieModel, MovieCastModel.movie_id == MovieModel.movie_id
            ).where(
                and_(
                    MovieCastModel.person_id == person_id,
                    MovieCastModel.department == 'Acting'
                )
            ).order_by(MovieCastModel.cast_order.nulls_last())
            
            acting_result = self.db.execute(acting_stmt)
            acting_credits = [
                MovieCredit(
                    movie_id=row.movie_id,
                    movie_title=row.title or f"영화 {row.movie_id}",
                    movie_poster_url=row.poster_url,
                    release_date=row.release_date,
                    character_name=row.character_name,
                    job=row.job,
                    department=row.department,
                    is_main_cast=row.is_main_cast
                ) for row in acting_result.fetchall()
            ]
            
            # 스태프 참여 작품 조회
            crew_stmt = select(
                MovieCastModel.movie_id,
                MovieModel.title,
                MovieModel.poster_url,
                MovieModel.release_date,
                MovieCastModel.character_name,
                MovieCastModel.job,
                MovieCastModel.department,
                MovieCastModel.is_main_cast
            ).select_from(
                MovieCastModel
            ).outerjoin(
                MovieModel, MovieCastModel.movie_id == MovieModel.movie_id
            ).where(
                and_(
                    MovieCastModel.person_id == person_id,
                    MovieCastModel.department != 'Acting'
                )
            )
            
            crew_result = self.db.execute(crew_stmt)
            crew_credits = [
                MovieCredit(
                    movie_id=row.movie_id,
                    movie_title=row.title or f"영화 {row.movie_id}",
                    movie_poster_url=row.poster_url,
                    release_date=row.release_date,
                    character_name=row.character_name,
                    job=row.job,
                    department=row.department,
                    is_main_cast=row.is_main_cast
                ) for row in crew_result.fetchall()
            ]
            
            total_movies = len(acting_credits) + len(crew_credits)
            
            return PersonCreditsResponse(
                person=person,
                acting_credits=acting_credits,
                crew_credits=crew_credits,
                total_movies=total_movies
            )
            
        except Exception as e:
            raise Exception(f"인물 작품 조회 실패: {str(e)}")
    
    async def search_persons(self, query: str, skip: int = 0, limit: int = 20) -> List[Person]:
        """인물 검색 (DB 먼저, 없으면 TMDB 검색)"""
        try:
            # 1. DB에서 먼저 검색
            stmt = select(PersonModel).where(
                or_(
                    PersonModel.name.ilike(f"%{query}%"),
                    PersonModel.original_name.ilike(f"%{query}%")
                )
            ).order_by(desc(PersonModel.popularity)).offset(skip).limit(limit)
            
            result = self.db.execute(stmt)
            persons = result.scalars().all()
            
            person_list = []
            for person_model in persons:
                followers_count = await self._get_person_followers_count(person_model.person_id)
                
                person_list.append(Person(
                    person_id=person_model.person_id,
                    name=person_model.name,
                    original_name=person_model.original_name,
                    biography=person_model.biography,
                    birthday=person_model.birthday,
                    deathday=person_model.deathday,
                    place_of_birth=person_model.place_of_birth,
                    profile_image_url=person_model.profile_image_url,
                    gender=person_model.gender,
                    known_for_department=person_model.known_for_department,
                    popularity=person_model.popularity,
                    is_adult=person_model.is_adult,
                    is_following=False,
                    followers_count=followers_count,
                    created_at=person_model.created_at,
                    updated_at=person_model.updated_at
                ))
            
            # 2. DB 결과가 부족하면 TMDB에서 추가 검색
            if len(person_list) < limit:
                tmdb_results = await self._search_persons_from_tmdb(query, limit - len(person_list))
                person_list.extend(tmdb_results)
            
            return person_list[:limit]
            
        except Exception as e:
            raise Exception(f"인물 검색 실패: {str(e)}")
    
    async def _search_persons_from_tmdb(self, query: str, limit: int) -> List[Person]:
        """TMDB에서 인물 검색하고 DB에 저장"""
        try:
            tmdb_results = await self.tmdb_service.search_person(query)
            if not tmdb_results or "results" not in tmdb_results:
                return []
            
            person_list = []
            for tmdb_person in tmdb_results["results"][:limit]:
                person_id = tmdb_person.get("id")
                if not person_id:
                    continue
                
                # DB에 이미 있는지 확인
                existing_person = await self.get_person_by_id(person_id)
                if existing_person:
                    person_list.append(existing_person)
            
            return person_list
            
        except Exception as e:
            print(f"TMDB 인물 검색 실패: {str(e)}")
            return []
    
    # 기존 follow 관련 메서드들...
    async def follow_person(self, user_id: int, person_id: int) -> PersonFollow:
        """인물 팔로우"""
        try:
            # 인물 존재 확인
            person = await self.get_person_by_id(person_id)
            if not person:
                raise Exception("존재하지 않는 인물입니다")
            
            # 이미 팔로우 중인지 확인
            if await self._is_following_person(user_id, person_id):
                raise Exception("이미 팔로우 중인 인물입니다")
            
            # 새 팔로우 관계 생성
            new_follow = PersonFollowModel(
                user_id=user_id,
                person_id=person_id
            )
            
            self.db.add(new_follow)
            self.db.commit()
            self.db.refresh(new_follow)
            
            return PersonFollow(
                user_id=new_follow.user_id,
                person_id=new_follow.person_id,
                created_at=new_follow.created_at
            )
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"인물 팔로우 실패: {str(e)}")
    
    async def unfollow_person(self, user_id: int, person_id: int) -> bool:
        """인물 언팔로우"""
        try:
            stmt = select(PersonFollowModel).where(
                and_(
                    PersonFollowModel.user_id == user_id,
                    PersonFollowModel.person_id == person_id
                )
            )
            result = self.db.execute(stmt)
            follow = result.scalar_one_or_none()
            
            if not follow:
                raise Exception("팔로우 관계를 찾을 수 없습니다")
            
            self.db.delete(follow)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"인물 언팔로우 실패: {str(e)}")
    
    async def _is_following_person(self, user_id: int, person_id: int) -> bool:
        """사용자가 인물을 팔로우하는지 확인"""
        try:
            stmt = select(PersonFollowModel).where(
                and_(
                    PersonFollowModel.user_id == user_id,
                    PersonFollowModel.person_id == person_id
                )
            )
            result = self.db.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception:
            return False
    
    async def _get_person_followers_count(self, person_id: int) -> int:
        """인물의 팔로워 수 조회"""
        try:
            stmt = select(func.count(PersonFollowModel.user_id)).where(
                PersonFollowModel.person_id == person_id
            )
            result = self.db.execute(stmt)
            return result.scalar() or 0
        except Exception:
            return 0
    
    def _parse_date(self, date_str: Optional[str]):
        """날짜 문자열을 date 객체로 변환"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    
    def _build_profile_image_url(self, path: Optional[str]) -> Optional[str]:
        """프로필 이미지 URL 생성"""
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/w500{path}"
    
    async def get_all_persons(self) -> list[Person]:
        """DB 전체 인물 조회"""
        try:
            stmt = select(PersonModel)
            result = self.db.execute(stmt)
            persons = []
            
            for person_model in result.scalars():
                persons.append(Person.from_orm(person_model))
            
            return persons
            
        except Exception as e:
            raise Exception(f"전체 인물 조회 실패: {str(e)}")
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
