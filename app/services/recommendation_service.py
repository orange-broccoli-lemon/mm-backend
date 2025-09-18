# app/services/recommendation_service.py

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc
import math
import random
from app.models.movie import MovieModel
from app.models.comment import CommentModel
from app.models.movie_genre import MovieGenreModel
from app.models.genre import GenreModel
from app.models.movie_cast import MovieCastModel
from app.models.person import PersonModel
from app.database import get_db


class RecommendationService:

    def __init__(self):
        self.db: Session = next(get_db())

    async def get_movie_recommendations(self, user_id: int, min_rating: float = 1.0) -> List[Dict]:
        """사용자 시청 기록 기반 영화 추천)"""
        try:
            # 1. 사용자 시청 기록 분석
            user_profile = await self._analyze_user_profile(user_id, min_rating)

            if not user_profile["watched_movies"]:
                # 시청 기록이 없으면 인기 영화 추천
                return await self._get_popular_movies()

            # 2. 랜덤 가중치 생성
            weights = self._generate_random_weights()

            # 3. 추천 점수 계산
            recommendations = await self._calculate_recommendation_scores(
                user_profile, user_id, weights
            )

            # 4. 점수 순으로 정렬하여 상위 3개 반환
            sorted_recommendations = sorted(
                recommendations.items(), key=lambda x: x[1], reverse=True
            )[:3]

            # 5. 영화 상세 정보와 함께 반환
            result = []
            for movie_id, score in sorted_recommendations:
                movie_info = await self._get_movie_info(movie_id)
                if movie_info:
                    movie_info["recommendation_score"] = round(score, 3)
                    result.append(movie_info)

            return result

        except Exception as e:
            print(f"영화 추천 실패: {str(e)}")
            return []

    def _generate_random_weights(self) -> Dict[str, float]:
        """매 요청마다 랜덤한 가중치 생성"""
        # 0.1 ~ 0.6 범위에서 랜덤 가중치 생성
        genre_weight = random.uniform(0.1, 0.6)
        people_weight = random.uniform(0.1, 0.6)
        rating_weight = random.uniform(0.1, 0.4)
        popularity_weight = random.uniform(0.05, 0.3)

        # 총합이 1이 되도록 정규화
        total = genre_weight + people_weight + rating_weight + popularity_weight

        return {
            "genre": genre_weight / total,
            "people": people_weight / total,
            "rating": rating_weight / total,
            "popularity": popularity_weight / total,
        }

    async def _analyze_user_profile(self, user_id: int, min_rating: float) -> Dict:
        """사용자 프로필 분석"""
        try:
            # 사용자가 평점을 남긴 영화들 조회
            stmt = (
                select(CommentModel.movie_id, CommentModel.rating)
                .where(
                    and_(
                        CommentModel.user_id == user_id,
                        CommentModel.rating >= min_rating,
                        CommentModel.is_public == True,
                    )
                )
                .order_by(desc(CommentModel.rating))
            )

            watched_movies = self.db.execute(stmt).all()

            if not watched_movies:
                return {"watched_movies": [], "preferred_genres": [], "preferred_people": []}

            movie_ids = [movie.movie_id for movie in watched_movies]

            # 선호 장르 분석
            preferred_genres = await self._get_preferred_genres(movie_ids)

            # 선호 배우/감독 분석
            preferred_people = await self._get_preferred_people(movie_ids)

            return {
                "watched_movies": movie_ids,
                "preferred_genres": preferred_genres,
                "preferred_people": preferred_people,
            }

        except Exception as e:
            print(f"사용자 프로필 분석 실패: {str(e)}")
            return {"watched_movies": [], "preferred_genres": [], "preferred_people": []}

    async def _get_preferred_genres(self, movie_ids: List[int]) -> List[int]:
        """선호 장르 ID 목록 반환"""
        try:
            stmt = (
                select(GenreModel.genre_id, func.count(MovieGenreModel.movie_id).label("count"))
                .join(MovieGenreModel, GenreModel.genre_id == MovieGenreModel.genre_id)
                .where(MovieGenreModel.movie_id.in_(movie_ids))
                .group_by(GenreModel.genre_id)
                .order_by(desc("count"))
                .limit(5)  # 상위 5개 장르만
            )

            result = self.db.execute(stmt).all()
            return [row.genre_id for row in result]

        except Exception as e:
            print(f"선호 장르 분석 실패: {str(e)}")
            return []

    async def _get_preferred_people(self, movie_ids: List[int]) -> List[int]:
        """선호 배우/감독 ID 목록 반환"""
        try:
            stmt = (
                select(MovieCastModel.person_id, func.count(MovieCastModel.movie_id).label("count"))
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
                .limit(10)  # 상위 10명만
            )

            result = self.db.execute(stmt).all()
            return [row.person_id for row in result]

        except Exception as e:
            print(f"선호 인물 분석 실패: {str(e)}")
            return []

    async def _calculate_recommendation_scores(
        self, user_profile: Dict, user_id: int, weights: Dict[str, float]
    ) -> Dict[int, float]:
        """추천 점수 계산 (랜덤 가중치 적용)"""
        try:
            watched_movie_ids = user_profile["watched_movies"]

            # 후보 영화들 조회 (이미 본 영화 제외)
            candidate_movies = await self._get_candidate_movies(watched_movie_ids)

            recommendations = {}

            for movie_id in candidate_movies:
                score = 0.0

                # 1. 장르 유사도 점수
                genre_score = await self._calculate_genre_similarity(
                    movie_id, user_profile["preferred_genres"]
                )
                score += genre_score * weights["genre"]

                # 2. 배우/감독 유사도 점수
                people_score = await self._calculate_people_similarity(
                    movie_id, user_profile["preferred_people"]
                )
                score += people_score * weights["people"]

                # 3. 평점 기반 점수
                rating_score = await self._calculate_rating_score(movie_id)
                score += rating_score * weights["rating"]

                # 4. 인기도 점수
                popularity_score = await self._calculate_popularity_score(movie_id)
                score += popularity_score * weights["popularity"]

                if score > 0:
                    recommendations[movie_id] = score

            return recommendations

        except Exception as e:
            print(f"추천 점수 계산 실패: {str(e)}")
            return {}

    async def _get_candidate_movies(self, watched_movie_ids: List[int]) -> List[int]:
        """추천 후보 영화들 조회"""
        try:
            stmt = select(MovieModel.movie_id).where(
                and_(
                    MovieModel.movie_id.notin_(watched_movie_ids) if watched_movie_ids else True,
                    MovieModel.average_rating >= 6.0,
                )
            )

            result = self.db.execute(stmt).all()
            return [row.movie_id for row in result]

        except Exception as e:
            print(f"후보 영화 조회 실패: {str(e)}")
            return []

    async def _calculate_genre_similarity(
        self, movie_id: int, preferred_genre_ids: List[int]
    ) -> float:
        """장르 유사도 계산"""
        try:
            if not preferred_genre_ids:
                return 0.0

            stmt = select(func.count(MovieGenreModel.genre_id)).where(
                and_(
                    MovieGenreModel.movie_id == movie_id,
                    MovieGenreModel.genre_id.in_(preferred_genre_ids),
                )
            )

            matching_count = self.db.execute(stmt).scalar() or 0
            return matching_count / len(preferred_genre_ids)

        except Exception as e:
            print(f"장르 유사도 계산 실패: {str(e)}")
            return 0.0

    async def _calculate_people_similarity(
        self, movie_id: int, preferred_people_ids: List[int]
    ) -> float:
        """배우/감독 유사도 계산"""
        try:
            if not preferred_people_ids:
                return 0.0

            stmt = select(func.count(MovieCastModel.person_id)).where(
                and_(
                    MovieCastModel.movie_id == movie_id,
                    MovieCastModel.person_id.in_(preferred_people_ids),
                )
            )

            matching_count = self.db.execute(stmt).scalar() or 0
            return matching_count / len(preferred_people_ids)

        except Exception as e:
            print(f"인물 유사도 계산 실패: {str(e)}")
            return 0.0

    async def _calculate_rating_score(self, movie_id: int) -> float:
        """평점 기반 점수 계산"""
        try:
            stmt = select(MovieModel.average_rating).where(MovieModel.movie_id == movie_id)
            result = self.db.execute(stmt).scalar_one_or_none()

            if result:
                return float(result) / 10.0  # 10점 만점을 1점 만점으로 정규화

            return 0.0

        except Exception as e:
            print(f"평점 점수 계산 실패: {str(e)}")
            return 0.0

    async def _calculate_popularity_score(self, movie_id: int) -> float:
        """인기도 점수 계산"""
        try:
            stmt = select(func.count(CommentModel.comment_id)).where(
                and_(CommentModel.movie_id == movie_id, CommentModel.is_public == True)
            )

            comment_count = self.db.execute(stmt).scalar() or 0
            return min(math.log(comment_count + 1) / 10.0, 1.0)  # 로그 스케일 정규화

        except Exception as e:
            print(f"인기도 점수 계산 실패: {str(e)}")
            return 0.0

    async def _get_movie_info(self, movie_id: int) -> Optional[Dict]:
        """영화 기본 정보 조회"""
        try:
            stmt = select(MovieModel).where(MovieModel.movie_id == movie_id)
            movie = self.db.execute(stmt).scalar_one_or_none()

            if movie:
                return {
                    "movie_id": movie.movie_id,
                    "title": movie.title,
                    "original_title": movie.original_title,
                    "overview": movie.overview,
                    "release_date": movie.release_date,
                    "poster_url": movie.poster_url,
                    "average_rating": float(movie.average_rating),
                    "runtime": movie.runtime,
                }

            return None

        except Exception as e:
            print(f"영화 정보 조회 실패: {str(e)}")
            return None

    async def _get_popular_movies(self) -> List[Dict]:
        """인기 영화 추천 (시청 기록이 없는 경우)"""
        try:
            stmt = (
                select(MovieModel)
                .where(MovieModel.average_rating >= 8.0)
                .order_by(desc(MovieModel.average_rating))
                .limit(3)
            )

            movies = self.db.execute(stmt).all()

            return [
                {
                    "movie_id": movie.movie_id,
                    "title": movie.title,
                    "original_title": movie.original_title,
                    "overview": movie.overview,
                    "release_date": movie.release_date,
                    "poster_url": movie.poster_url,
                    "average_rating": float(movie.average_rating),
                    "runtime": movie.runtime,
                    "recommendation_score": float(movie.average_rating) / 10.0,
                }
                for movie in movies
            ]

        except Exception as e:
            print(f"인기 영화 조회 실패: {str(e)}")
            return []

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()
