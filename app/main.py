# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import get_settings
from app.api.v1 import api_router
from app.database import engine, Base

# 설정 로드
settings = get_settings()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# FastAPI 앱 생성
# 프록시 경로에 맞춰 FastAPI 앱 생성
app = FastAPI(
    title="mM",
    description="Movie Community Service",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    root_path="/api",
    servers=[{"url": "/api"}],
)


# OpenAPI 스키마
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="mM",
        version="1.0.0",
        openapi_version="3.0.2",
        description="Movie Community Service",
        routes=app.routes,
        servers=[{"url": "/api"}],
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

ALLOWED_ORIGINS = ["http://localhost:5173", "https://i13m105.p.ssafy.io"]

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 라우터 등록
app.include_router(api_router, prefix="/v1")


@app.get("/")
def read_root():
    """서비스 루트"""
    return {
        "service": "mM",
        "description": "Movie Community Service",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/profilebot/{text}/{review}")
def read_root(text: str, review: str):
    return profile_reviewbot(text, [review])
