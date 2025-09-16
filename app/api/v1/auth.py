# app/api/v1/auth.py

from fastapi import APIRouter, HTTPException, Depends
from app.schemas.user import (
    User, UserCreateEmail, UserCreateGoogle, 
    UserLoginEmail, UserLoginGoogle, EmailCheck, TokenResponse
)
from app.services.user_service import UserService
from app.core.auth import create_access_token
from app.services.google_oauth_service import GoogleOAuthService

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


@router.get(
    "/google/login",
    summary="Google 로그인 URL 생성",
    description="Google OAuth 로그인을 위한 URL을 생성합니다."
)
async def google_login():
    google_service = GoogleOAuthService()
    login_url = google_service.get_login_url()
    return {"url": login_url}

@router.get(
    "/google/callback", 
    response_model=TokenResponse,
    summary="Google OAuth 콜백",
    description="Google OAuth 인증 후 콜백을 처리합니다."
)
async def google_callback(
    code: str,
    user_service: UserService = Depends(get_user_service)
):
    google_service = GoogleOAuthService()
    user_info = google_service.get_user_info_from_code(code)
    
    if not user_info:
        raise HTTPException(status_code=400, detail="Google 인증 실패")
    
    # 기존 사용자 확인 또는 새 사용자 생성
    user = await user_service.authenticate_user_google(
        email=user_info["email"],
        google_id=user_info["id"]
    )
    
    if not user:
        # 새 사용자 생성
        user_data = UserCreateGoogle(
            google_id=user_info["id"],
            email=user_info["email"],
            name=user_info["name"],
            profile_image_url=user_info.get("picture")
        )
        user = await user_service.create_user_google(user_data)
    
    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token, user=user)