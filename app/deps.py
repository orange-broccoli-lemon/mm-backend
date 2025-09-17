# app/deps.py

import torch
from transformers import (
    MarianMTModel,
    MarianTokenizer,
    pipeline,
    BertTokenizer,
    BertForSequenceClassification,
    AutoTokenizer,
    AutoModelForSequenceClassification,
)
from openai import AsyncOpenAI
import os
import asyncio
from typing import List

# 로컬 경로로 변경
mt_model_dir = "/app/huggingface_models/ko-en"
zero_shot_model_dir = "/app/huggingface_models/zero-shot"


mt_tokenizer = MarianTokenizer.from_pretrained(mt_model_dir)
mt_model = MarianMTModel.from_pretrained(mt_model_dir)
mt_model.eval()
classifier = pipeline("zero-shot-classification", model=zero_shot_model_dir)


def ko_to_en(text):
    batch = mt_tokenizer([text], return_tensors="pt", truncation=True, padding=True)
    gen = mt_model.generate(**batch)
    eng_text = mt_tokenizer.decode(gen[0], skip_special_tokens=True)
    return eng_text


def spoiler_detect_zero_shot(text):
    candidate_labels = ["spoiler", "not spoiler"]
    result = classifier(text, candidate_labels)
    if result["labels"][0] == "spoiler":
        return {"is_spoiler": 1, "spoiler_score": result["scores"][0]}

    return {"is_spoiler": 0, "spoiler_score": result["scores"][1]}


def check_spoiler_ko(text_ko):
    eng_text = ko_to_en(text_ko)
    result_label = spoiler_detect_zero_shot(eng_text)
    return result_label


em_model_dir = "/app/huggingface_models/naver_review_model/"

em_tokenizer = BertTokenizer.from_pretrained(em_model_dir)
em_model = BertForSequenceClassification.from_pretrained(em_model_dir)

em_model.eval()


# 단일 텍스트 감정 분석 함수
def check_emotion_ko(text_ko):
    inputs = em_tokenizer(text_ko, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = em_model(**inputs)
        logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)
    prediction = torch.argmax(probabilities, dim=1).item()
    return {"is_positive": prediction, "confidence": probabilities[0][1].item()}


# 모델명 혹은 로컬 경로
model_name = "jinkyeongk/kcELECTRA-toxic-detector"

# 토크나이저와 모델 로드
to_tokenizer = AutoTokenizer.from_pretrained(model_name)
to_model = AutoModelForSequenceClassification.from_pretrained(model_name)
to_model.eval()  # 평가 모드로 변경


def detect_toxicity(text):
    inputs = to_tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = to_model(**inputs)
        logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)
    prediction = torch.argmax(probabilities, dim=1).item()
    return {"is_toxic": prediction, "confidence": probabilities[0][1].item()}


# GMS(LLM Aggregator) API BASE_URL
client = AsyncOpenAI(base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1")


def findbot(user_content: str):
    async def inner():
        res_text = ""
        stream = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": """당신은 find bot이라는 이름의 긍정 에너지 가득한 영화 찾기 전문 AI입니다.

**핵심 역할:**
- 오직 구체적인 영화를 찾아주는 요청에만 답변합니다
- 사용자가 기억하는 영화의 일부 정보를 바탕으로 정확한 영화 제목을 찾아서 알려줍니다

**허용되는 질문 유형:**
- "~한 장면이 있는 영화 제목이 뭐야?"
- "~배우가 나오고 ~한 내용인 영화 찾아줘"
- "~라는 대사가 나오는 영화 찾아줘"
- "줄거리가 ~인 영화 제목 알려줘"
- "OST에 ~노래가 나오는 영화 찾아줘"

**거절할 질문 유형:**
- 추천 요청 ("~한 영화 추천해줘", "볼만한 영화 알려줘")
- 영화 정보 문의 ("~영화 줄거리 알려줘", "~배우가 누구야?")
- 평가/리뷰 ("~영화 어때?", "평점이 얼마야?")
- 순위/랭킹 ("박스오피스 1위가 뭐야?", "최고의 영화는?")
- 영화 외 다른 주제 (드라마, 책, 음악 등)

**거절 시 응답:**
"죄송합니다! 저는 이미 존재하는 영화의 제목을 찾아드리는 일만 할 수 있어요. 
'~한 장면이 나오는 영화 제목이 뭐야?' 또는 '~배우가 나오는 ~한 내용의 영화 찾아줘' 
같은 식으로 구체적인 영화 찾기 질문을 해주세요! 😊"

**답변 스타일:**
반드시 아래 3가지 항목을 순서대로 포함하여 답변하세요:

1. **🎬 영화 제목:** 
   - 정확한 영화 제목 (출시연도 포함)

2. **🔍 추측 근거:** 
   - 사용자가 제시한 정보와 해당 영화가 일치하는 이유
   - 어떤 단서들이 이 영화를 특정하게 했는지 설명

3. **📖 줄거리:** 
   - 해당 영화의 간단한 줄거리 (3-4줄 정도)
   - 사용자가 기억하는 내용이 맞는지 확인할 수 있는 수준으로 작성
""",
                },
                {"role": "user", "content": user_content},
            ],
            max_tokens=1024,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                res_text += chunk.choices[0].delta.content
        return res_text

    return asyncio.run(inner())


# uvicorn app.main:app --reload
# 대답 형태를 제목 근거 줄거리 세로로 나오게


def concise_reviewbot(movie_title: str, reviews: List[str]):
    async def inner():
        prompt = f"""당신은 Concise Review Bot입니다.\
        
영화 '{movie_title}'에 대한 아래 리뷰들을 바탕으로 4~5문장으로 간단하게 평가를 요약해 주세요.\
- 긍정적·부정적·중립적 관점 모두 반영\
- 별점은 생략하고 핵심 코멘트만 제시"""

        stream = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "\\n".join(reviews)},
            ],
            max_tokens=500,
            stream=True,
        )
        res_text = ""
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                res_text += chunk.choices[0].delta.content
        return res_text

    return asyncio.run(inner())


def profile_reviewbot(reviewer_name: str, reviews: List[str]):
    """
    reviewer_name: 프로필을 요약할 사람 이름
    reviews: 해당 리뷰어가 작성한 여러 리뷰 문자열 리스트

    역할:
    - 리뷰어의 스타일, 선호도, 성향을 파악하여 간단한 프로필 작성
    - 각 리뷰의 주요 특징(긍정·부정·중립 키워드, 자주 언급하는 주제 등)을 종합
    - 프로필과 리뷰 요약(4~5문장)으로 응답
    """

    async def inner():
        prompt = f"""당신은 Review Profile Bot입니다.

'{reviewer_name}'라는 이름의 리뷰어가 아래 리뷰들을 작성했습니다:
{chr(10).join(f"- {r}" for r in reviews)}

이 리뷰들을 분석하여:
1. 리뷰어의 전반적인 성향과 선호도 (예: 어떤 요소에 집중하는지, 스타일)
2. 리뷰 작성 시 자주 사용하는 표현이나 키워드
3. 이 리뷰어에 대한 간단한 프로필 (4~5문장)

위 항목을 포함해 4~5문장으로 요약해 주세요."""
        stream = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": ""}],
            max_tokens=500,
            stream=True,
        )
        result = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                result += content
        return result

    return asyncio.run(inner())
