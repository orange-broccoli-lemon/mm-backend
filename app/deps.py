# app/deps.py

import torch
from transformers import MarianMTModel, MarianTokenizer
from transformers import pipeline

# 1. 한글 -> 영어 번역 모델 로딩
mt_model_name = "Helsinki-NLP/opus-mt-ko-en"
mt_tokenizer = MarianTokenizer.from_pretrained(mt_model_name)
mt_model = MarianMTModel.from_pretrained(mt_model_name)

# 2. zero-shot 분류 파이프라인 로딩 (facebook/bart-large-mnli)
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def ko_to_en(text):
    batch = mt_tokenizer([text], return_tensors="pt", truncation=True, padding=True)
    gen = mt_model.generate(**batch)
    eng_text = mt_tokenizer.decode(gen[0], skip_special_tokens=True)
    return eng_text

def spoiler_detect_zero_shot(text):
    # label 후보 2개: 스포일러, 비스포일러
    candidate_labels = ["spoiler", "not spoiler"]
    result = classifier(text, candidate_labels)
    # 가장 높은 점수를 받은 라벨 반환
    return result['labels'][0]

# 3. 전체 파이프라인 / spoiler or not spoiler 출력
def check_spoiler_ko(text_ko):
    eng_text = ko_to_en(text_ko)
    print(f"Translated: {eng_text}")
    result_label = spoiler_detect_zero_shot(eng_text)
    return result_label
