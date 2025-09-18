# app/services/person_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc, or_
from app.models.person import PersonModel
from app.models.person_follow import PersonFollowModel
from app.models.movie_cast import MovieCastModel
from app.models.movie import MovieModel
from app.schemas.person import (
    Person,
    PersonFollow,
    PersonStats,
    PersonCreditsResponse,
    MovieCredit,
    PersonFeedItem,
    PersonFeedResponse,
)
from app.services.tmdb_service import TMDBService
from app.database import SessionLocal


class PersonService:

    def __init__(self):
        self.tmdb_service = TMDBService()

    def _get_db(self) -> Session:
        """데이터베이스 세션 생성"""
        return SessionLocal()

    async def get_person_by_id(
        self, person_id: int, current_user_id: Optional[int] = None
    ) -> Optional[Person]:
        """인물 상세 정보 조회"""
        db = self._get_db()
        try:
            # 1. DB에서 먼저 조회
            person_model = self._get_person_model_by_id(person_id, db)

            # 2. DB에 없거나 상세 정보가 없으면 TMDB에서 업데이트
            if not person_model or not person_model.biography:
                person_model = await self._update_person_details_from_tmdb_with_db(
                    person_id, person_model, db
                )
                if not person_model:
                    return None

            # 3. Person 스키마로 변환
            is_following = False
            if current_user_id:
                is_following = self._is_following_person_with_db(current_user_id, person_id, db)

            followers_count = self._get_person_followers_count_with_db(person_id, db)

            return self._build_person_response(person_model, is_following, followers_count)

        except Exception as e:
            raise Exception(f"인물 조회 실패: {str(e)}")
        finally:
            db.close()

    async def get_person_credits(self, person_id: int) -> PersonCreditsResponse:
        """인물의 영화 출연 작품 조회"""
        db = self._get_db()
        try:
            person = await self._get_person_basic_info(person_id, db)
            if not person:
                raise Exception("존재하지 않는 인물입니다")

            # 출연 작품 조회
            acting_credits = self._get_person_acting_credits(person_id, db)
            # 스태프 참여 작품 조회
            crew_credits = self._get_person_crew_credits(person_id, db)

            total_movies = len(acting_credits) + len(crew_credits)

            return PersonCreditsResponse(
                person=person,
                acting_credits=acting_credits,
                crew_credits=crew_credits,
                total_movies=total_movies,
            )

        except Exception as e:
            raise Exception(f"인물 작품 조회 실패: {str(e)}")
        finally:
            db.close()

    async def search_persons(self, query: str, skip: int = 0, limit: int = 20) -> List[Person]:
        """인물 검색"""
        db = self._get_db()
        try:
            # 1. DB에서 먼저 검색
            persons_from_db = self._search_persons_in_db(query, skip, limit, db)

            # 2. DB 결과가 부족하면 TMDB에서 추가 검색
            if len(persons_from_db) < limit:
                tmdb_results = await self._search_persons_from_tmdb(
                    query, limit - len(persons_from_db)
                )
                persons_from_db.extend(tmdb_results)

            return persons_from_db[:limit]

        except Exception as e:
            raise Exception(f"인물 검색 실패: {str(e)}")
        finally:
            db.close()

    async def follow_person(self, user_id: int, person_id: int) -> PersonFollow:
        """인물 팔로우"""
        db = self._get_db()
        try:
            # 인물 존재 확인
            if not self._person_exists(person_id, db):
                raise Exception("존재하지 않는 인물입니다")

            # 이미 팔로우 중인지 확인
            if self._is_following_person_with_db(user_id, person_id, db):
                raise Exception("이미 팔로우 중인 인물입니다")

            # 새 팔로우 관계 생성
            new_follow = PersonFollowModel(user_id=user_id, person_id=person_id)

            db.add(new_follow)
            db.commit()
            db.refresh(new_follow)

            return PersonFollow(
                user_id=new_follow.user_id,
                person_id=new_follow.person_id,
                created_at=new_follow.created_at,
            )

        except Exception as e:
            db.rollback()
            raise Exception(f"인물 팔로우 실패: {str(e)}")
        finally:
            db.close()

    async def unfollow_person(self, user_id: int, person_id: int) -> bool:
        """인물 언팔로우"""
        db = self._get_db()
        try:
            stmt = select(PersonFollowModel).where(
                and_(PersonFollowModel.user_id == user_id, PersonFollowModel.person_id == person_id)
            )
            result = db.execute(stmt)
            follow = result.scalar_one_or_none()

            if not follow:
                raise Exception("팔로우 관계를 찾을 수 없습니다")

            db.delete(follow)
            db.commit()

            return True

        except Exception as e:
            db.rollback()
            raise Exception(f"인물 언팔로우 실패: {str(e)}")
        finally:
            db.close()

    async def get_all_persons(self) -> list[Person]:
        """DB 전체 인물 조회"""
        db = self._get_db()
        try:
            stmt = select(PersonModel)
            result = db.execute(stmt)
            persons = []

            for person_model in result.scalars():
                persons.append(Person.from_orm(person_model))

            return persons

        except Exception as e:
            raise Exception(f"전체 인물 조회 실패: {str(e)}")
        finally:
            db.close()

    async def _update_person_details_from_tmdb_with_db(
        self, person_id: int, existing_person: Optional[PersonModel], db: Session
    ) -> Optional[PersonModel]:
        """TMDB에서 인물 상세 정보로 업데이트 + 영화 기본 정보와 movie_cast 저장"""
        try:
            # 1. TMDB에서 인물 상세 정보 조회
            tmdb_data = await self.tmdb_service.get_person_details(person_id)
            if not tmdb_data:
                return existing_person

            if existing_person:
                # 기존 기본 정보를 상세 정보로 업데이트
                self._update_existing_person(existing_person, tmdb_data)
                db.commit()
                db.refresh(existing_person)
                person_model = existing_person
            else:
                # 새로 생성
                person_model = self._create_new_person_from_tmdb(tmdb_data)
                db.add(person_model)
                db.commit()
                db.refresh(person_model)

            # 3. 영화 기본 정보 + movie_cast 저장
            await self._save_person_movie_cast_with_movie_basic_db(person_id, db)

            return person_model

        except Exception as e:
            db.rollback()
            return existing_person

    async def _save_person_movie_cast_with_movie_basic_db(self, person_id: int, db: Session):
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
                await self._ensure_movie_basic_info_db(
                    movie_id=movie_id,
                    title=cast.get("title", ""),
                    poster_path=cast.get("poster_path"),
                    release_date=cast.get("release_date"),
                    db=db,
                )

                # movie_cast 연결 저장
                await self._ensure_movie_cast_connection_db(
                    movie_id=movie_id,
                    person_id=person_id,
                    character_name=cast.get("character"),
                    job="Actor",
                    department="Acting",
                    cast_order=cast.get("order", 999),
                    is_main_cast=cast.get("order", 999) < 10,
                    db=db,
                )

            # 스태프 참여 작품 저장
            crew_credits = credits_data.get("crew", [])
            for crew in crew_credits:
                movie_id = crew.get("id")
                if not movie_id:
                    continue

                # 주요 역할만 저장
                if crew.get("job") in [
                    "Director",
                    "Producer",
                    "Executive Producer",
                    "Screenplay",
                    "Story",
                    "Director of Photography",
                ]:
                    # 영화 기본 정보 저장
                    await self._ensure_movie_basic_info_db(
                        movie_id=movie_id,
                        title=crew.get("title", ""),
                        poster_path=crew.get("poster_path"),
                        release_date=crew.get("release_date"),
                        db=db,
                    )

                    # movie_cast 연결 저장
                    await self._ensure_movie_cast_connection_db(
                        movie_id=movie_id,
                        person_id=person_id,
                        character_name=None,
                        job=crew.get("job"),
                        department=crew.get("department"),
                        cast_order=None,
                        is_main_cast=crew.get("job") in ["Director", "Producer"],
                        db=db,
                    )

        except Exception:
            pass

    async def _ensure_movie_basic_info_db(
        self,
        movie_id: int,
        title: str,
        poster_path: Optional[str],
        release_date: Optional[str],
        db: Session,
    ):
        """영화 기본 정보만 저장"""
        try:
            if not self._movie_exists(movie_id, db):
                from decimal import Decimal

                basic_movie = MovieModel(
                    movie_id=movie_id,
                    title=title,
                    original_title=None,
                    overview=None,
                    release_date=self._parse_date(release_date),
                    runtime=None,
                    poster_url=self._build_image_url(poster_path, "w500"),
                    backdrop_url=None,
                    average_rating=Decimal("0.0"),
                    is_adult=False,
                    trailer_url=None,
                )
                db.add(basic_movie)
                db.commit()

        except Exception:
            db.rollback()

    async def _ensure_movie_cast_connection_db(
        self,
        movie_id: int,
        person_id: int,
        character_name: Optional[str],
        job: Optional[str],
        department: Optional[str],
        cast_order: Optional[int],
        is_main_cast: bool,
        db: Session,
    ):
        """movie_cast 연결 중복 체크 후 저장"""
        try:
            if not self._movie_cast_connection_exists(movie_id, person_id, job, db):
                new_cast = MovieCastModel(
                    movie_id=movie_id,
                    person_id=person_id,
                    character_name=character_name,
                    job=job,
                    department=department,
                    cast_order=cast_order,
                    is_main_cast=is_main_cast,
                )
                db.add(new_cast)
                db.commit()

        except Exception:
            db.rollback()

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

        except Exception:
            return []

    def _get_person_model_by_id(self, person_id: int, db: Session) -> Optional[PersonModel]:
        """인물 모델 조회"""
        stmt = select(PersonModel).where(PersonModel.person_id == person_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_person_basic_info(self, person_id: int, db: Session) -> Optional[Person]:
        """인물 기본 정보 조회"""
        person_model = self._get_person_model_by_id(person_id, db)
        if not person_model:
            return None

        followers_count = self._get_person_followers_count_with_db(person_id, db)
        return self._build_person_response(person_model, False, followers_count)

    def _get_person_acting_credits(self, person_id: int, db: Session) -> List[MovieCredit]:
        """출연 작품 조회"""
        acting_stmt = (
            select(
                MovieCastModel.movie_id,
                MovieModel.title,
                MovieModel.poster_url,
                MovieModel.release_date,
                MovieCastModel.character_name,
                MovieCastModel.job,
                MovieCastModel.department,
                MovieCastModel.is_main_cast,
            )
            .select_from(MovieCastModel)
            .outerjoin(MovieModel, MovieCastModel.movie_id == MovieModel.movie_id)
            .where(
                and_(MovieCastModel.person_id == person_id, MovieCastModel.department == "Acting")
            )
            .order_by(MovieCastModel.cast_order.nulls_last())
        )

        acting_result = db.execute(acting_stmt)
        return [
            MovieCredit(
                movie_id=row.movie_id,
                movie_title=row.title or f"영화 {row.movie_id}",
                movie_poster_url=row.poster_url,
                release_date=row.release_date,
                character_name=row.character_name,
                job=row.job,
                department=row.department,
                is_main_cast=row.is_main_cast,
            )
            for row in acting_result.fetchall()
        ]

    def _get_person_crew_credits(self, person_id: int, db: Session) -> List[MovieCredit]:
        """스태프 참여 작품 조회"""
        crew_stmt = (
            select(
                MovieCastModel.movie_id,
                MovieModel.title,
                MovieModel.poster_url,
                MovieModel.release_date,
                MovieCastModel.character_name,
                MovieCastModel.job,
                MovieCastModel.department,
                MovieCastModel.is_main_cast,
            )
            .select_from(MovieCastModel)
            .outerjoin(MovieModel, MovieCastModel.movie_id == MovieModel.movie_id)
            .where(
                and_(MovieCastModel.person_id == person_id, MovieCastModel.department != "Acting")
            )
        )

        crew_result = db.execute(crew_stmt)
        return [
            MovieCredit(
                movie_id=row.movie_id,
                movie_title=row.title or f"영화 {row.movie_id}",
                movie_poster_url=row.poster_url,
                release_date=row.release_date,
                character_name=row.character_name,
                job=row.job,
                department=row.department,
                is_main_cast=row.is_main_cast,
            )
            for row in crew_result.fetchall()
        ]

    def _search_persons_in_db(self, query: str, skip: int, limit: int, db: Session) -> List[Person]:
        """DB에서 인물 검색"""
        stmt = (
            select(PersonModel)
            .where(
                or_(
                    PersonModel.name.ilike(f"%{query}%"),
                    PersonModel.original_name.ilike(f"%{query}%"),
                )
            )
            .order_by(desc(PersonModel.popularity))
            .offset(skip)
            .limit(limit)
        )

        result = db.execute(stmt)
        persons = result.scalars().all()

        person_list = []
        for person_model in persons:
            followers_count = self._get_person_followers_count_with_db(person_model.person_id, db)
            person_list.append(self._build_person_response(person_model, False, followers_count))

        return person_list

    def _is_following_person_with_db(self, user_id: int, person_id: int, db: Session) -> bool:
        """사용자가 인물을 팔로우하는지 확인"""
        try:
            stmt = select(PersonFollowModel).where(
                and_(PersonFollowModel.user_id == user_id, PersonFollowModel.person_id == person_id)
            )
            result = db.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception:
            return False

    def _get_person_followers_count_with_db(self, person_id: int, db: Session) -> int:
        """인물의 팔로워 수 조회"""
        try:
            stmt = select(func.count(PersonFollowModel.user_id)).where(
                PersonFollowModel.person_id == person_id
            )
            result = db.execute(stmt)
            return result.scalar() or 0
        except Exception:
            return 0

    def _person_exists(self, person_id: int, db: Session) -> bool:
        """인물 존재 여부 확인"""
        return self._get_person_model_by_id(person_id, db) is not None

    def _movie_exists(self, movie_id: int, db: Session) -> bool:
        """영화 존재 여부 확인"""
        stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _movie_cast_connection_exists(
        self, movie_id: int, person_id: int, job: str, db: Session
    ) -> bool:
        """movie_cast 연결 존재 여부 확인"""
        stmt = select(MovieCastModel).where(
            and_(
                MovieCastModel.movie_id == movie_id,
                MovieCastModel.person_id == person_id,
                MovieCastModel.job == job,
            )
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _update_existing_person(self, existing_person: PersonModel, tmdb_data: dict):
        """기존 인물 정보를 TMDB 데이터로 업데이트"""
        existing_person.name = tmdb_data.get("name", existing_person.name)
        existing_person.original_name = (
            tmdb_data.get("also_known_as", [None])[0] if tmdb_data.get("also_known_as") else None
        )
        existing_person.biography = tmdb_data.get("biography")
        existing_person.birthday = self._parse_date(tmdb_data.get("birthday"))
        existing_person.deathday = self._parse_date(tmdb_data.get("deathday"))
        existing_person.place_of_birth = tmdb_data.get("place_of_birth")
        existing_person.gender = tmdb_data.get("gender", 0)
        existing_person.popularity = int(tmdb_data.get("popularity", 0))
        existing_person.is_adult = tmdb_data.get("adult", False)

        # 더 좋은 프로필 이미지로 업데이트
        if tmdb_data.get("profile_path"):
            existing_person.profile_image_url = self._build_profile_image_url(
                tmdb_data.get("profile_path")
            )

    def _create_new_person_from_tmdb(self, tmdb_data: dict) -> PersonModel:
        """TMDB 데이터로 새 인물 생성"""
        return PersonModel(
            person_id=tmdb_data.get("id"),
            name=tmdb_data.get("name", ""),
            original_name=(
                tmdb_data.get("also_known_as", [None])[0]
                if tmdb_data.get("also_known_as")
                else None
            ),
            biography=tmdb_data.get("biography"),
            birthday=self._parse_date(tmdb_data.get("birthday")),
            deathday=self._parse_date(tmdb_data.get("deathday")),
            place_of_birth=tmdb_data.get("place_of_birth"),
            profile_image_url=self._build_profile_image_url(tmdb_data.get("profile_path")),
            gender=tmdb_data.get("gender", 0),
            known_for_department=tmdb_data.get("known_for_department"),
            popularity=int(tmdb_data.get("popularity", 0)),
            is_adult=tmdb_data.get("adult", False),
        )

    def _build_person_response(
        self, person_model: PersonModel, is_following: bool, followers_count: int
    ) -> Person:
        """Person 응답 객체 생성"""
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
            updated_at=person_model.updated_at,
        )

    # 유틸리티 메서드들
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

    def _build_image_url(self, path: Optional[str], size: str) -> Optional[str]:
        """이미지 URL 생성"""
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/{size}{path}"
