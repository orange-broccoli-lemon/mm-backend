# app/api/v1/system.py

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.database import engine

router = APIRouter()


@router.get("/health")
def health_check():
    """서비스 헬스체크"""
    return {"status": "healthy", "service": "mM"}


@router.get("/db-test")
def test_db():
    """데이터베이스 연결 테스트"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return {"status": "DB 연결 성공!", "result": result.fetchone()[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 연결 실패: {str(e)}")
