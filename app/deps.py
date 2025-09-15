# app/deps.py

import torch
from transformers import MarianMTModel, MarianTokenizer, pipeline

# 로컬 경로로 변경
mt_model_dir = "/app/huggingface_models/ko-en"
zero_shot_model_dir = "/app/huggingface_models/zero-shot"

mt_tokenizer = MarianTokenizer.from_pretrained(mt_model_dir)
mt_model = MarianMTModel.from_pretrained(mt_model_dir)

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
