

from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_name = "jinkyeongk/kcELECTRA-toxic-detector"
save_dir = "/app/huggingface_models/kcELECTRA-toxic-detector"

# 토크나이저와 모델 다운로드 후 로컬 폴더에 저장
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

tokenizer.save_pretrained(save_dir)
model.save_pretrained(save_dir)

print(f"모델과 토크나이저가 {save_dir}에 저장되었습니다.")