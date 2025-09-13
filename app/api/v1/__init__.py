from fastapi import APIRouter
from . import movies, search, system

api_router = APIRouter()

# 각 모듈의 라우터 등록
api_router.include_router(movies.router, prefix="/movies", tags=["영화"])
api_router.include_router(search.router, prefix="/search", tags=["검색"])
api_router.include_router(system.router, prefix="/system", tags=["시스템"])
