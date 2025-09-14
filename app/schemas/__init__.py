# app/schemas/__init__.py

from .movie import Movie
from .search import MovieSearchResult, PersonSearchResult, SearchResult, SearchResponse

__all__ = [
    "Movie", 
    "MovieSearchResult", 
    "PersonSearchResult", 
    "SearchResult", 
    "SearchResponse"
]
