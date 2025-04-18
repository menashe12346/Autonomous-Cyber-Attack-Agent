from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_path = "/mnt/linux-data/project/code/models/hf_models/mistral"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float32)  # לא float16 על CPU

# קלט לדוגמה
input_text = "Once upon a time"
inputs = tokenizer(input_text, return_tensors="pt")

# הפקת טקסט
outputs = model.generate(**inputs, max_new_tokens=50)
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

print(generated_text)
