# app/services/prompt_service.py

import yaml
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any


class PromptService:
    """프롬프트 관리 서비스"""

    def __init__(self, prompts_file: str = "prompts.yaml"):
        self.prompts_file = Path(prompts_file)
        self._prompts_cache = None

    @lru_cache(maxsize=1)
    def _load_prompts(self) -> Dict[str, Any]:
        """YAML 파일에서 프롬프트 로드"""
        try:
            if not self.prompts_file.exists():
                print(f"Warning: {self.prompts_file} 파일을 찾을 수 없습니다.")
                return {}

            with open(self.prompts_file, "r", encoding="utf-8") as f:
                prompts = yaml.safe_load(f)
                print(f"프롬프트 로드 완료: {self.prompts_file}")
                return prompts or {}
        except Exception as e:
            print(f"프롬프트 로드 실패: {str(e)}")
            return {}

    def get_prompt(self, category: str, prompt_type: str) -> str:
        """특정 프롬프트 가져오기"""
        prompts = self._load_prompts()

        try:
            return prompts[category][prompt_type]
        except KeyError:
            print(f"Warning: 프롬프트를 찾을 수 없습니다: {category}.{prompt_type}")
            return ""

    def get_findbot_prompt(self) -> str:
        """Find Bot 시스템 프롬프트"""
        return self.get_prompt("findbot", "system_prompt")

    def get_concise_review_prompt(self) -> str:
        """리뷰 요약 프롬프트"""
        return self.get_prompt("review_bot", "concise_prompt")

    def get_profile_review_prompt(self) -> str:
        """프로필 분석 프롬프트"""
        return self.get_prompt("review_bot", "profile_prompt")

    def reload_prompts(self):
        """프롬프트 캐시 초기화 (런타임에서 리로드)"""
        self._load_prompts.cache_clear()
        print("프롬프트 캐시가 초기화되었습니다.")


# 전역 인스턴스
prompt_service = PromptService()
