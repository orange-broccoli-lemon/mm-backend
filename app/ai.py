# app/ai.py

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
from app.core.config import get_settings
from app.services.prompt_service import prompt_service

# 설정 로드
settings = get_settings()

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


def check_emotion_ko(text_ko):
    inputs = em_tokenizer(text_ko, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = em_model(**inputs)
        logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)
    prediction = torch.argmax(probabilities, dim=1).item()
    return {"is_positive": prediction, "confidence": probabilities[0][1].item()}


model_name = "jinkyeongk/kcELECTRA-toxic-detector"

to_tokenizer = AutoTokenizer.from_pretrained(model_name)
to_model = AutoModelForSequenceClassification.from_pretrained(model_name)
to_model.eval()


def detect_toxicity(text):
    inputs = to_tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = to_model(**inputs)
        logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)
    prediction = torch.argmax(probabilities, dim=1).item()
    return {"is_toxic": prediction, "confidence": probabilities[0][1].item()}


# OpenAI 클라이언트
client = AsyncOpenAI(base_url=settings.openai_base_url)


async def findbot(user_content: str):
    """영화 찾기"""
    system_prompt = prompt_service.get_findbot_prompt()

    res_text = ""
    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=1024,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            res_text += chunk.choices[0].delta.content
    return res_text


async def concise_reviewbot(movie_title: str, reviews: List[str]):
    """리뷰 요약"""
    prompt_template = prompt_service.get_concise_review_prompt()
    prompt = prompt_template.replace("{movie_title}", movie_title)

    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "\\n".join(reviews)},
        ],
        max_tokens=500,
        stream=True,
    )
    result = ""
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            result += content
    return result


async def profile_reviewbot(reviewer_name: str, reviews: List[str]):
    """프로필 분석"""
    prompt_template = prompt_service.get_profile_review_prompt()
    prompt = prompt_template.replace("{reviewer_name}", reviewer_name)

    reviews_text = chr(10).join(f"- {r}" for r in reviews)
    full_prompt = f"{prompt}\n\n{reviews_text}"

    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": ""},
        ],
        max_tokens=500,
        stream=True,
    )
    result = ""
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            result += content
    return result
