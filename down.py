from transformers import MarianMTModel, MarianTokenizer, pipeline

mt_model_name = "Helsinki-NLP/opus-mt-ko-en"
mt_model = MarianMTModel.from_pretrained(mt_model_name)
mt_tokenizer = MarianTokenizer.from_pretrained(mt_model_name)
mt_model.save_pretrained("/srv/huggingface_models/ko-en")
mt_tokenizer.save_pretrained("/srv/huggingface_models/ko-en")

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
classifier.model.save_pretrained("/srv/huggingface_models/zero-shot")
classifier.tokenizer.save_pretrained("/srv/huggingface_models/zero-shot")


from transformers import BertTokenizer, BertForSequenceClassification
from huggingface_hub import login

# Hugging Face 로그인 (터미널 로그인 대신 코드 내 토큰 사용 가능)
login(token="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")

model_name = "blockenters/finetuned-nsmc-sentiment"

# 토크나이저와 모델을 다운로드하여 로컬 캐시에 저장
tokenizer = BertTokenizer.from_pretrained(model_name, use_auth_token=True)
model = BertForSequenceClassification.from_pretrained(model_name, use_auth_token=True)

# 로컬에 원하는 디렉토리로 저장
save_directory = "/srv/huggingface_models/naver_review_model"
tokenizer.save_pretrained(save_directory)
model.save_pretrained(save_directory)

print(f"모델과 토크나이저를 {save_directory}에 저장 완료")


from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_name = "jinkyeongk/kcELECTRA-toxic-detector"
save_dir = "/srv/huggingface_models/toxic_ko"

# 토크나이저와 모델 다운로드 후 로컬 폴더에 저장
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

tokenizer.save_pretrained(save_dir)
model.save_pretrained(save_dir)

print(f"모델과 토크나이저가 {save_dir}에 저장되었습니다.")

