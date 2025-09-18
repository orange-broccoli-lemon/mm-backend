# app/schemas/__init__.py

from .movie import Movie
from .user import (
    User,
    UserCreateEmail,
    UserCreateGoogle,
    UserLoginEmail,
    EmailCheck,
    TokenResponse,
)
from .person import (
    Person,
    PersonFollow,
    PersonFollowRequest,
    PersonStats,
    PersonCreditsResponse,
    PersonFeedResponse,
)
from .user_movie import UserMovie, WatchStatus
from .comment import Comment, CommentCreate, CommentUpdate
from .movie_cast import MovieCast, CastRole
from .search import MovieSearchResult, PersonSearchResult, SearchResult, SearchResponse
from .genre import Genre, GenreListResponse

__all__ = [
    "Movie",
    "User",
    "UserCreateEmail",
    "UserCreateGoogle",
    "UserLoginEmail",
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
    "GenreListResponse",
    "CommentCreate",
    "CommentUpdate",
    "PersonFollow",
    "PersonFollowRequest",
    "PersonStats",
    "PersonCreditsResponse",
    "PersonFeedResponse",
]
