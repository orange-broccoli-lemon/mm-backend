# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import get_settings
from app.api.v1 import api_router
from app.database import engine, Base
import asyncio
from contextlib import asynccontextmanager
from app.services.scheduler_service import SchedulerService

# 설정 로드
settings = get_settings()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 스케줄러 전역 변수
scheduler_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    global scheduler_task
    scheduler_service = SchedulerService()
    scheduler_task = asyncio.create_task(scheduler_service.run_scheduler())
    print("프로필 분석 스케줄러 시작됨")

    yield

    # 종료 시
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    print("프로필 분석 스케줄러 종료됨")


# FastAPI 앱 생성
app = FastAPI(
    title="mM",
    description="Movie Community Service",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    root_path="/api",
    servers=[{"url": "/api"}],
    lifespan=lifespan,
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
