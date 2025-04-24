from transformers import AutoModelForCausalLM, AutoTokenizer

# שם המודל על HuggingFace
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# נתיב שמותאם לפקודת האימון שלך
save_path = "/mnt/linux-data/project/code/models/hf_models/mistral"

print(f"[🚀] Downloading TinyLlama model ({model_name})...")
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

print(f"[💾] Saving model and tokenizer to: {save_path}")
model.save_pretrained(save_path)
tokenizer.save_pretrained(save_path)

print("[✅] Done! You can now run your training script.")
