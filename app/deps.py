# app/deps.py

import torch
from transformers import MarianMTModel, MarianTokenizer, pipeline, BertTokenizer, BertForSequenceClassification, AutoTokenizer, AutoModelForSequenceClassification

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
    if (result['labels'][0] == "spoiler"):
        return { "is_spoiler" : 1, "spoiler_score" : result['scores'][0]}
    
    return { "is_spoiler" : 0, "spoiler_score" : result['scores'][1]}


def check_spiler_ko(text_ko):
    eng_text = ko_to_en(text_ko)
    result_label = spoiler_detect_zero_shot(eng_text)
    return result_label

em_model_dir = "/app/huggingface_models/naver_review_model/"

em_tokenizer = BertTokenizer.from_pretrained(em_model_dir)
em_model = BertForSequenceClassification.from_pretrained(em_model_dir)

em_model.eval()

# 단일 텍스트 감정 분석 함수
def check_emotion_ko(text_ko):
    inputs = em_tokenizer(text_ko, return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        outputs = em_model(**inputs)
        logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)
    prediction = torch.argmax(probabilities, dim=1).item()
    return { "is_positive" : prediction, "confidence" : probabilities[0][1].item()}


# 모델명 혹은 로컬 경로
model_name = "jinkyeongk/kcELECTRA-toxic-detector"

# 토크나이저와 모델 로드
to_tokenizer = AutoTokenizer.from_pretrained(model_name)
to_model = AutoModelForSequenceClassification.from_pretrained(model_name)
to_model.eval()  # 평가 모드로 변경

def detect_toxicity(text):
    inputs = to_tokenizer(text, return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        outputs = to_model(**inputs)
        logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)
    prediction = torch.argmax(probabilities, dim=1).item()
    return { "is_toxic" : prediction, "confidence" : probabilities[0][1].item()}