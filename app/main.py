from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1 import api_router

# 설정 로드
settings = get_settings()

# FastAPI 앱 생성
app = FastAPI(
    title="mM",
    description="Movie Community Service", 
    version="1.0.0"
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 라우터 등록
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    """서비스 루트"""
    return {
        "service": "mM",
        "description": "Movie Community Service",
        "version": "1.0.0",
        "docs": "/docs"
    }
