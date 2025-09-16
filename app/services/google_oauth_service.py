# app/services/google_oauth_service.py


import requests
from typing import Optional, Dict
from fastapi import HTTPException
from app.core.config import get_settings

class GoogleOAuthService:
    def __init__(self):
        self.settings = get_settings()
        
    def get_login_url(self) -> str:
        """Google 로그인 URL 생성"""
        params = {
            "response_type": "code",
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "scope": "openid email profile"
        }
        
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    def get_user_info_from_code(self, code: str) -> Optional[Dict]:
        """Google 인증 코드로 사용자 정보 조회"""
        try:
            # 1. 인증 코드를 액세스 토큰으로 교환
            token_response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                }
            )
            
            if token_response.status_code != 200:
                return None
                
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                return None
                
            # 2. 액세스 토큰으로 사용자 정보 조회
            user_info = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_info.status_code != 200:
                return None
                
            return user_info.json()
            
        except Exception as e:
            print(f"Google OAuth error: {str(e)}")
            return None
