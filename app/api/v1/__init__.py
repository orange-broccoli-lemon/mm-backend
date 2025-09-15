# app/api/v1/__init__.py

from fastapi import APIRouter
from . import movies, search, system, auth, comments, follows, feed, genres

api_router = APIRouter()

api_router.include_router(movies.router, prefix="/movies", tags=["영화"])
api_router.include_router(search.router, prefix="/search", tags=["검색"])
api_router.include_router(system.router, prefix="/system", tags=["시스템"])
api_router.include_router(auth.router, prefix="/auth", tags=["인증"])
api_router.include_router(comments.router, prefix="/comments", tags=["댓글"])
api_router.include_router(follows.router, prefix="/follows", tags=["팔로우"])
api_router.include_router(feed.router, prefix="/feed", tags=["피드"])
api_router.include_router(genres.router, prefix="/genres", tags=["장르"])
