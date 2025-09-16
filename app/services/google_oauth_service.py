# app/services/google_oauth_service.py

from typing import Dict
from fastapi import HTTPException

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.core.config import get_settings

class GoogleOAuthService:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.google_client_id:
            raise RuntimeError("google_client_id is not configured")

    def verify_id_token(self, id_token_str: str) -> Dict:
        """
        프런트에서 받은 Google ID 토큰을 서버 로컬에서 검증하고 payload를 반환.
        검증 실패 시 HTTPException(400).
        """
        try:
            req = google_requests.Request()
            payload = google_id_token.verify_oauth2_token(
                id_token_str,
                req,
                self.settings.google_client_id,
            )

            return payload
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Google ID token: {str(e)}")
