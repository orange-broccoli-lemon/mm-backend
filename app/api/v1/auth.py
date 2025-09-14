# app/api/v1/auth.py

from fastapi import APIRouter, HTTPException, Depends
from app.schemas.user import (
    User, UserCreateEmail, UserCreateGoogle, 
    UserLoginEmail, UserLoginGoogle, EmailCheck, TokenResponse
)
from app.services.user_service import UserService
from app.core.auth import create_access_token

router = APIRouter()

def get_user_service() -> UserService:
    return UserService()

# 이메일 회원가입
@router.post(
    "/signup/email",
    response_model=TokenResponse,
    summary="이메일 회원가입",
    description="이메일과 비밀번호로 회원가입합니다."
)
async def signup_email(
    user_data: UserCreateEmail,
    user_service: UserService = Depends(get_user_service)
):
    try:
        user = await user_service.create_user_email(user_data)
        access_token = create_access_token(data={"sub": user.email})
        
        return TokenResponse(
            access_token=access_token,
            user=user
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 구글 회원가입
@router.post(
    "/signup/google",
    response_model=TokenResponse,
    summary="구글 회원가입",
    description="Google 계정으로 회원가입합니다."
)
async def signup_google(
    user_data: UserCreateGoogle,
    user_service: UserService = Depends(get_user_service)
):
    try:
        user = await user_service.create_user_google(user_data)
        access_token = create_access_token(data={"sub": user.email})
        
        return TokenResponse(
            access_token=access_token,
            user=user
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 이메일 로그인
@router.post(
    "/login/email",
    response_model=TokenResponse,
    summary="이메일 로그인",
    description="이메일과 비밀번호로 로그인합니다."
)
async def login_email(
    login_data: UserLoginEmail,
    user_service: UserService = Depends(get_user_service)
):
    try:
        user = await user_service.authenticate_user_email(
            email=login_data.email,
            password=login_data.password
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다")
        
        access_token = create_access_token(data={"sub": user.email})
        
        return TokenResponse(
            access_token=access_token,
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이메일 로그인 실패: {str(e)}")

# 구글 로그인
@router.post(
    "/login/google",
    response_model=TokenResponse,
    summary="구글 로그인",
    description="Google 계정으로 로그인합니다."
)
async def login_google(
    login_data: UserLoginGoogle,
    user_service: UserService = Depends(get_user_service)
):
    try:
        user = await user_service.authenticate_user_google(
            email=login_data.email,
            google_id=login_data.google_id
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="잘못된 Google 로그인 정보입니다")
        
        access_token = create_access_token(data={"sub": user.email})
        
        return TokenResponse(
            access_token=access_token,
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google 로그인 실패: {str(e)}")

# 이메일 중복 체크
@router.post(
    "/check-email",
    summary="이메일 중복 체크",
    description="이메일이 이미 등록되어 있는지 확인합니다."
)
async def check_email(
    email_data: EmailCheck,
    user_service: UserService = Depends(get_user_service)
):
    try:
        exists = await user_service.check_email_exists(email_data.email)
        
        return {
            "email": email_data.email,
            "exists": exists,
            "message": "이미 등록된 이메일입니다" if exists else "사용 가능한 이메일입니다"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이메일 확인 실패: {str(e)}")
