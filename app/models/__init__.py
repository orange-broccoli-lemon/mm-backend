# app/models/__init__.py

from .movie import MovieModel
from .user import UserModel
from .genre import GenreModel
from .person import PersonModel
from .user_follow import UserFollowModel
from .movie_genre import MovieGenreModel
from .user_movie import UserMovieModel
from .comment import CommentModel
from .comment_like import CommentLikeModel
from .movie_cast import MovieCastModel
from .person_follow import PersonFollowModel


__all__ = [
    "MovieModel",
    "UserModel",
    "GenreModel",
    "PersonModel",
    "UserFollowModel",
    "MovieGenreModel",
    "UserMovieModel",
    "CommentModel",
    "CommentLikeModel",
    "MovieCastModel",
    "PersonFollowModel",
]
