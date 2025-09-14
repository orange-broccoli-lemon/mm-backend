# app/models/__init__.py

from .movie import MovieModel

__all__ = [
    "MovieModel",
    "UserModel",
    "GenreModel",
    "PersonModel",
    "UserFollowModel",
    "MovieGenreModel",
]
