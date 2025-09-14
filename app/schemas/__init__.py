# app/schemas/__init__.py

from .movie import Movie
from .user import (
    User, UserCreateEmail, UserCreateGoogle, 
    UserLoginEmail, UserLoginGoogle, EmailCheck, TokenResponse
)
from .person import Person
from .user_movie import UserMovie, WatchStatus
from .comment import Comment
from .movie_cast import MovieCast, CastRole
from .search import MovieSearchResult, PersonSearchResult, SearchResult, SearchResponse
from .genre import Genre, GenreListResponse

__all__ = [
    "Movie",
    "User",
    "UserCreateEmail",
    "UserCreateGoogle", 
    "UserLoginEmail",
    "UserLoginGoogle",
    "EmailCheck",
    "TokenResponse",
    "Person",
    "UserMovie",
    "WatchStatus",
    "Comment",
    "MovieCast",
    "CastRole",
    "MovieSearchResult", 
    "PersonSearchResult", 
    "SearchResult", 
    "SearchResponse",
    "Genre",
    "GenreListResponse"
]
