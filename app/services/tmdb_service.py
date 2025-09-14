# app/services/tmdb_service.py

from typing import List, Optional
import httpx
from datetime import datetime
from decimal import Decimal
from app.core.config import get_settings
from app.schemas import Movie, MovieSearchResult, PersonSearchResult, SearchResult

class TMDBService:
    
    def __init__(self):
        self.settings = get_settings()
        self.timeout = httpx.Timeout(self.settings.tmdb_timeout)
        self.default_language = "ko-KR"
    
    def _get_image_url(self, path: str, size: str = "w500") -> Optional[str]:
        if not path:
            return None
        return f"{self.settings.tmdb_image_base_url}{size}{path}"
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime.date]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    
    def _format_movie_to_erd(self, movie_data: dict) -> Movie:
        return Movie(
            movie_id=movie_data.get("id"),
            title=movie_data.get("title", ""),
            original_title=movie_data.get("original_title"),
            overview=movie_data.get("overview"),
            release_date=self._parse_date(movie_data.get("release_date")),
            runtime=movie_data.get("runtime"),
            poster_url=self._get_image_url(movie_data.get("poster_path"), "w500"),
            backdrop_url=self._get_image_url(movie_data.get("backdrop_path"), "w1280"),
            average_rating=Decimal(str(movie_data.get("vote_average", 0.0))),
            is_adult=movie_data.get("adult", False),
            trailer_url=self._extract_trailer_url(movie_data)
        )
    
    def _extract_trailer_url(self, movie_data: dict) -> Optional[str]:
        videos = movie_data.get("videos", {}).get("results", [])
        for video in videos:
            if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                return f"https://www.youtube.com/watch?v={video.get('key')}"
        return None
    
    async def get_popular_movies_top10(self, language: str = None) -> List[Movie]:
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
                
                movies = []
                for movie_data in data.get("results", [])[:10]:
                    formatted_movie = self._format_movie_to_erd(movie_data)
                    movies.append(formatted_movie)
                
                return movies
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"TMDB API 오류: {e.response.status_code}")
            except httpx.RequestError as e:
                raise Exception(f"요청 실패: {str(e)}")
    
    async def get_movie_details(self, movie_id: int, language: str = None) -> dict:
        if language is None:
            language = self.default_language
            
        url = f"{self.settings.tmdb_base_url}/movie/{movie_id}"
        
        params = {
            "language": language,
            "append_to_response": "videos"
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
                
                return data
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise Exception(f"영화를 찾을 수 없습니다 (ID: {movie_id})")
                raise Exception(f"TMDB API 오류: {e.response.status_code}")
            except httpx.RequestError as e:
                raise Exception(f"요청 실패: {str(e)}")
    
    async def multi_search(self, query: str, language: str = None) -> List[SearchResult]:
        if language is None:
            language = self.default_language
            
        url = f"{self.settings.tmdb_base_url}/search/multi"
        
        params = {
            "query": query,
            "language": language,
            "page": 1,
            "region": "KR",
            "include_adult": "false"
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
                
                results = []
                for result_data in data.get("results", []):
                    media_type = result_data.get("media_type")
                    
                    if media_type == "movie":
                        movie_result = MovieSearchResult(
                            id=result_data.get("id"),
                            media_type="movie",
                            title=result_data.get("title", ""),
                            overview=result_data.get("overview"),
                            release_date=self._parse_date(result_data.get("release_date")),
                            poster_path=result_data.get("poster_path"),
                            vote_average=result_data.get("vote_average", 0.0)
                        )
                        results.append(movie_result)
                    
                    elif media_type == "person":
                        person_result = PersonSearchResult(
                            id=result_data.get("id"),
                            media_type="person",
                            name=result_data.get("name", ""),
                            profile_path=result_data.get("profile_path")
                        )
                        results.append(person_result)
                
                return results
                
            except httpx.HTTPStatusError as e:
                raise Exception(f"TMDB API 오류: {e.response.status_code}")
            except httpx.RequestError as e:
                raise Exception(f"요청 실패: {str(e)}")
