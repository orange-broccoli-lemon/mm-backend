# app/services/recommendation_service.py

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc
import math
import random
import httpx
from app.models.movie import MovieModel
from app.models.comment import CommentModel
from app.models.movie_genre import MovieGenreModel
from app.models.genre import GenreModel
from app.models.movie_cast import MovieCastModel
from app.database import SessionLocal
from app.core.config import get_settings


class RecommendationService:

    def __init__(self):
        self.settings = get_settings()

    def _get_db(self) -> Session:
        """데이터베이스 세션 생성"""
        return SessionLocal()

    async def get_movie_recommendations(self, user_id: int) -> List[Dict]:
        """사용자 시청 기록 기반 영화 추천 (5개)"""
        db = self._get_db()
        try:
            user_profile = await self._analyze_user_profile_with_db(user_id, db)

            if not user_profile["watched_movies"]:
                return await self._get_popular_movies_with_db(5, db)

            # 자체 알고리즘 3개 + TMDB API 2개
            internal_recs = await self._get_internal_recommendations_with_db(user_profile, db)
            tmdb_recs = await self._get_tmdb_recommendations(user_profile["latest_movie"])

            # 중복 제거 후 최종 5개 반환
            all_recs = await self._merge_recommendations_with_db(
                internal_recs, tmdb_recs, user_profile["watched_movies"], db
            )
            return [self._to_simple_format(movie) for movie in all_recs[:5]]

        except Exception as e:
            return []
        finally:
            db.close()

    async def _analyze_user_profile_with_db(self, user_id: int, db: Session) -> Dict:
        """사용자 시청 기록 및 선호도 분석"""
        try:
            # 사용자 시청 기록 조회
            stmt = (
                select(CommentModel.movie_id, CommentModel.created_at)
                .where(
                    and_(
                        CommentModel.user_id == user_id,
                        CommentModel.rating >= 1.0,  # 고정값
                        CommentModel.is_public == True,
                    )
                )
                .order_by(desc(CommentModel.created_at))
            )

            watched_movies = db.execute(stmt).all()
            if not watched_movies:
                return {
                    "watched_movies": [],
                    "preferred_genres": [],
                    "preferred_people": [],
                    "latest_movie": None,
                }

            movie_ids = [movie.movie_id for movie in watched_movies]
            return {
                "watched_movies": movie_ids,
                "preferred_genres": await self._get_preferred_genres_with_db(movie_ids, db),
                "preferred_people": await self._get_preferred_people_with_db(movie_ids, db),
                "latest_movie": watched_movies[0].movie_id,
            }

        except Exception:
            return {
                "watched_movies": [],
                "preferred_genres": [],
                "preferred_people": [],
                "latest_movie": None,
            }

    async def _get_preferred_genres_with_db(self, movie_ids: List[int], db: Session) -> List[int]:
        """선호 장르 ID 목록 (상위 5개)"""
        try:
            stmt = (
                select(GenreModel.genre_id, func.count().label("count"))
                .join(MovieGenreModel, GenreModel.genre_id == MovieGenreModel.genre_id)
                .where(MovieGenreModel.movie_id.in_(movie_ids))
                .group_by(GenreModel.genre_id)
                .order_by(desc("count"))
                .limit(5)
            )
            return [row.genre_id for row in db.execute(stmt).all()]
        except Exception:
            return []

    async def _get_preferred_people_with_db(self, movie_ids: List[int], db: Session) -> List[int]:
        """선호 배우/감독 ID 목록 (상위 10개)"""
        try:
            stmt = (
                select(MovieCastModel.person_id, func.count().label("count"))
                .where(
                    and_(
                        MovieCastModel.movie_id.in_(movie_ids),
                        or_(
                            MovieCastModel.department == "Acting",
                            and_(
                                MovieCastModel.department == "Directing",
                                MovieCastModel.job == "Director",
                            ),
                        ),
                    )
                )
                .group_by(MovieCastModel.person_id)
                .order_by(desc("count"))
                .limit(10)
            )
            return [row.person_id for row in db.execute(stmt).all()]
        except Exception:
            return []

    async def _get_internal_recommendations_with_db(
        self, user_profile: Dict, db: Session
    ) -> List[Dict]:
        """자체 알고리즘으로 3개 추천"""
        try:
            weights = self._generate_random_weights()
            scores = await self._calculate_recommendation_scores_with_db(user_profile, weights, db)

            # 상위 3개 선택
            top_movies = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]

            result = []
            for movie_id, score in top_movies:
                movie_info = await self._get_movie_basic_info_with_db(movie_id, db)
                if movie_info:
                    movie_info["recommendation_score"] = score
                    result.append(movie_info)

            return result
        except Exception:
            return []

    async def _get_tmdb_recommendations(self, latest_movie_id: Optional[int]) -> List[Dict]:
        """TMDB API로 2개 추천"""
        try:
            if not latest_movie_id:
                return []

            url = f"{self.settings.tmdb_base_url}/movie/{latest_movie_id}/recommendations"
            params = {"api_key": self.settings.tmdb_api_key, "language": "ko-KR", "page": 1}

            timeout = httpx.Timeout(self.settings.tmdb_timeout)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=self.settings.tmdb_headers)

                if response.status_code != 200:
                    return []

                results = response.json().get("results", [])
                if not results:
                    return []

                # 상위 결과에서 2개 선택
                selected_count = min(2, len(results))
                selected = (
                    random.sample(results[:8], selected_count)
                    if len(results) >= 4
                    else results[:selected_count]
                )

                return [
                    {
                        "movie_id": movie.get("id"),
                        "title": movie.get("title", ""),
                        "poster_url": self._build_image_url(movie.get("poster_path")),
                        "recommendation_score": 0.5,
                    }
                    for movie in selected
                    if movie.get("id")
                ]

        except Exception:
            return []

    async def _merge_recommendations_with_db(
        self,
        internal_recs: List[Dict],
        tmdb_recs: List[Dict],
        watched_movies: List[int],
        db: Session,
    ) -> List[Dict]:
        """추천 결과 합치기"""
        all_recs = []
        seen_ids = set(watched_movies)

        # 자체 추천 추가
        for rec in internal_recs:
            if rec["movie_id"] not in seen_ids:
                all_recs.append(rec)
                seen_ids.add(rec["movie_id"])

        # TMDB 추천 추가
        for rec in tmdb_recs:
            if rec["movie_id"] not in seen_ids:
                all_recs.append(rec)
                seen_ids.add(rec["movie_id"])

        # 5개 미만이면 인기 영화로 채우기
        if len(all_recs) < 5:
            popular = await self._get_popular_movies_with_db(5 - len(all_recs), db, list(seen_ids))
            for movie in popular:
                if len(all_recs) < 5:
                    movie["recommendation_score"] = 0.3
                    all_recs.append(movie)

        # 점수 순 정렬
        all_recs.sort(key=lambda x: x.get("recommendation_score", 0), reverse=True)
        return all_recs

    async def _calculate_recommendation_scores_with_db(
        self, user_profile: Dict, weights: Dict[str, float], db: Session
    ) -> Dict[int, float]:
        """추천 점수 계산"""
        try:
            # 후보 영화들 조회
            stmt = select(MovieModel.movie_id, MovieModel.average_rating).where(
                and_(
                    (
                        MovieModel.movie_id.notin_(user_profile["watched_movies"])
                        if user_profile["watched_movies"]
                        else True
                    ),
                    MovieModel.average_rating >= 6.0,
                )
            )

            candidates = db.execute(stmt).all()
            scores = {}

            for movie_id, rating in candidates:
                score = 0.0

                # 장르 유사도
                score += (
                    await self._calculate_genre_similarity_with_db(
                        movie_id, user_profile["preferred_genres"], db
                    )
                    * weights["genre"]
                )

                # 인물 유사도
                score += (
                    await self._calculate_people_similarity_with_db(
                        movie_id, user_profile["preferred_people"], db
                    )
                    * weights["people"]
                )

                # 평점 점수
                score += (float(rating) / 10.0) * weights["rating"]

                # 인기도 점수
                score += (
                    await self._calculate_popularity_score_with_db(movie_id, db)
                    * weights["popularity"]
                )

                if score > 0:
                    scores[movie_id] = score

            return scores
        except Exception:
            return {}

    async def _calculate_genre_similarity_with_db(
        self, movie_id: int, preferred_genres: List[int], db: Session
    ) -> float:
        """장르 유사도 계산"""
        if not preferred_genres:
            return 0.0

        stmt = select(func.count()).where(
            and_(
                MovieGenreModel.movie_id == movie_id, MovieGenreModel.genre_id.in_(preferred_genres)
            )
        )

        matching = db.execute(stmt).scalar() or 0
        return matching / len(preferred_genres)

    async def _calculate_people_similarity_with_db(
        self, movie_id: int, preferred_people: List[int], db: Session
    ) -> float:
        """배우/감독 유사도 계산"""
        if not preferred_people:
            return 0.0

        stmt = select(func.count()).where(
            and_(
                MovieCastModel.movie_id == movie_id, MovieCastModel.person_id.in_(preferred_people)
            )
        )

        matching = db.execute(stmt).scalar() or 0
        return matching / len(preferred_people)

    async def _calculate_popularity_score_with_db(self, movie_id: int, db: Session) -> float:
        """인기도 점수 계산"""
        stmt = select(func.count()).where(
            and_(CommentModel.movie_id == movie_id, CommentModel.is_public == True)
        )

        comment_count = db.execute(stmt).scalar() or 0
        return min(math.log(comment_count + 1) / 10.0, 1.0)

    async def _get_movie_basic_info_with_db(self, movie_id: int, db: Session) -> Optional[Dict]:
        """영화 기본 정보 조회"""
        stmt = select(MovieModel.movie_id, MovieModel.title, MovieModel.poster_url).where(
            MovieModel.movie_id == movie_id
        )
        result = db.execute(stmt).first()

        if result:
            return {
                "movie_id": result.movie_id,
                "title": result.title,
                "poster_url": result.poster_url,
            }
        return None

    async def _get_popular_movies_with_db(
        self, count: int, db: Session, exclude_ids: List[int] = None
    ) -> List[Dict]:
        """인기 영화 조회"""
        exclude_ids = exclude_ids or []

        stmt = (
            select(MovieModel.movie_id, MovieModel.title, MovieModel.poster_url)
            .where(
                and_(
                    MovieModel.average_rating >= 8.0,
                    MovieModel.movie_id.notin_(exclude_ids) if exclude_ids else True,
                )
            )
            .order_by(desc(MovieModel.average_rating))
            .limit(count)
        )

        return [
            {"movie_id": row.movie_id, "title": row.title, "poster_url": row.poster_url}
            for row in db.execute(stmt).all()
        ]

    def _generate_random_weights(self) -> Dict[str, float]:
        """랜덤 가중치 생성"""
        weights = {
            "genre": random.uniform(0.1, 0.6),
            "people": random.uniform(0.1, 0.6),
            "rating": random.uniform(0.1, 0.4),
            "popularity": random.uniform(0.05, 0.3),
        }

        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

    def _build_image_url(self, path: Optional[str]) -> Optional[str]:
        """TMDB 이미지 URL 생성"""
        return f"{self.settings.tmdb_image_base_url}w500{path}" if path else None

    def _to_simple_format(self, movie: Dict) -> Dict:
        """간단한 형식으로 변환"""
        return {
            "movie_id": movie["movie_id"],
            "title": movie["title"],
            "poster_url": movie.get("poster_url"),
        }

    async def _analyze_user_profile(self, user_id: int) -> Dict:
        """사용자 시청 기록 및 선호도 분석"""
        db = self._get_db()
        try:
            return await self._analyze_user_profile_with_db(user_id, db)
        finally:
            db.close()

    async def _get_preferred_genres(self, movie_ids: List[int]) -> List[int]:
        """선호 장르 ID 목록 (상위 5개)"""
        db = self._get_db()
        try:
            return await self._get_preferred_genres_with_db(movie_ids, db)
        finally:
            db.close()

    async def _get_preferred_people(self, movie_ids: List[int]) -> List[int]:
        """선호 배우/감독 ID 목록 (상위 10개)"""
        db = self._get_db()
        try:
            return await self._get_preferred_people_with_db(movie_ids, db)
        finally:
            db.close()

    async def _get_internal_recommendations(self, user_profile: Dict) -> List[Dict]:
        """자체 알고리즘으로 3개 추천"""
        db = self._get_db()
        try:
            return await self._get_internal_recommendations_with_db(user_profile, db)
        finally:
            db.close()

    async def _merge_recommendations(
        self, internal_recs: List[Dict], tmdb_recs: List[Dict], watched_movies: List[int]
    ) -> List[Dict]:
        """추천 결과 합치기"""
        db = self._get_db()
        try:
            return await self._merge_recommendations_with_db(
                internal_recs, tmdb_recs, watched_movies, db
            )
        finally:
            db.close()

    async def _calculate_recommendation_scores(
        self, user_profile: Dict, weights: Dict[str, float]
    ) -> Dict[int, float]:
        """추천 점수 계산"""
        db = self._get_db()
        try:
            return await self._calculate_recommendation_scores_with_db(user_profile, weights, db)
        finally:
            db.close()

    async def _calculate_genre_similarity(
        self, movie_id: int, preferred_genres: List[int]
    ) -> float:
        """장르 유사도 계산"""
        db = self._get_db()
        try:
            return await self._calculate_genre_similarity_with_db(movie_id, preferred_genres, db)
        finally:
            db.close()

    async def _calculate_people_similarity(
        self, movie_id: int, preferred_people: List[int]
    ) -> float:
        """배우/감독 유사도 계산"""
        db = self._get_db()
        try:
            return await self._calculate_people_similarity_with_db(movie_id, preferred_people, db)
        finally:
            db.close()

    async def _calculate_popularity_score(self, movie_id: int) -> float:
        """인기도 점수 계산"""
        db = self._get_db()
        try:
            return await self._calculate_popularity_score_with_db(movie_id, db)
        finally:
            db.close()

    async def _get_movie_basic_info(self, movie_id: int) -> Optional[Dict]:
        """영화 기본 정보 조회"""
        db = self._get_db()
        try:
            return await self._get_movie_basic_info_with_db(movie_id, db)
        finally:
            db.close()

    async def _get_popular_movies(self, count: int, exclude_ids: List[int] = None) -> List[Dict]:
        """인기 영화 조회"""
        db = self._get_db()
        try:
            return await self._get_popular_movies_with_db(count, db, exclude_ids)
        finally:
            db.close()
