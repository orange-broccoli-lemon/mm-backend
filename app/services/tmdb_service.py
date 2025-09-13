from typing import List, Optional
import httpx
from datetime import datetime
from app.core.config import get_settings
from app.schemas import Movie

class TMDBService:
    """TMDB API 통신 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.timeout = httpx.Timeout(self.settings.tmdb_timeout)
        self.default_language = "ko-KR"
    
    def _get_image_url(self, path: str, size: str = "w500") -> Optional[str]:
        """이미지 URL 생성"""
        if not path:
            return None
        return f"{self.settings.tmdb_image_base_url}{size}{path}"
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime.date]:
        """날짜 문자열을 date 객체로 변환"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    
    def _format_movie(self, movie_data: dict) -> Movie:
        """TMDB 응답 데이터를 Movie 모델로 변환"""
        return Movie(
            tmdb_id=movie_data.get("id"),
            title=movie_data.get("title", ""),
            original_title=movie_data.get("original_title", ""),
            overview=movie_data.get("overview"),
            release_date=self._parse_date(movie_data.get("release_date")),
            runtime=None,  # popular API에서는 제공하지 않음
            poster_url=self._get_image_url(movie_data.get("poster_path"), "w500"),
            backdrop_url=self._get_image_url(movie_data.get("backdrop_path"), "w1280"),
            average_rating=round(movie_data.get("vote_average", 0.0), 2),
            is_adult=movie_data.get("adult", False),
            trailer_url=None,  # popular API에서는 제공하지 않음
            vote_average=movie_data.get("vote_average", 0.0),
            vote_count=movie_data.get("vote_count", 0),
            popularity=movie_data.get("popularity", 0.0),
            genre_ids=movie_data.get("genre_ids", []),
            original_language=movie_data.get("original_language", "")
        )
    
    async def get_popular_movies_top10(self, language: str = None) -> List[Movie]:
        """인기 영화 10개 조회"""
        if language is None:
            language = self.default_language
            
        url = f"{self.settings.tmdb_base_url}/movie/popular"
        
        params = {
            "language": language,
            "page": 1,
            "region": "KR"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.settings.tmdb_headers
                )
                response.raise_for_status()
                data = response.json()
                
                # 10개만 추출하고 포맷팅
                movies = []
                for movie_data in data.get("results", [])[:10]:
                    formatted_movie = self._format_movie(movie_data)
                    movies.append(formatted_movie)
                
                return movies
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"TMDB API 오류: {e.response.status_code}")
            except httpx.RequestError as e:
                raise Exception(f"요청 실패: {str(e)}")
