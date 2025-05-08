import os
import subprocess
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel, PeftConfig

# === שלב 1: הורדת מודל HuggingFace (Mistral 7B) ===
def download_base_model():
    base_model = "mistralai/Mistral-7B-v0.1"
    target_dir = "/mnt/linux-data/project/code/models/hf_models/mistral"
    print(f"📦 Downloading base model: {base_model}")
    snapshot_download(repo_id=base_model, local_dir=target_dir, local_dir_use_symlinks=False)
    print("✅ Download completed.")

# === שלב 2: הרצת Fine-Tuning עם llama-factory ===
def run_finetuning():
    config_path = "/mnt/linux-data/project/code/configs/finetune_parser.yaml"
    llama_factory_dir = "/mnt/linux-data/project/code/models/llama-factory"
    print("🚀 Running fine-tuning...")
    subprocess.run(["python", "src/train.py", config_path], cwd=llama_factory_dir, check=True)
    print("✅ Fine-tuning complete.")

# === שלב 3: מיזוג LoRA לתוך המודל ===
def merge_lora():
    base_model_path = "/mnt/linux-data/project/code/models/hf_models/mistral"
    lora_model_path = "/mnt/linux-data/project/code/models/finetuned_models/nous_hermes_parser_lora"
    merged_output_path = "/mnt/linux-data/project/code/models/merged_model"

    print("🔄 Merging LoRA into base model...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_path)
    base_model = AutoModelForCausalLM.from_pretrained(base_model_path, torch_dtype="auto")
    model = PeftModel.from_pretrained(base_model, lora_model_path)
    model = model.merge_and_unload()

    model.save_pretrained(merged_output_path, safe_serialization=True)
    tokenizer.save_pretrained(merged_output_path)
    print("✅ LoRA merged successfully.")

# === שלב 4: המרת HuggingFace ל־GGUF (llama.cpp) ===
def convert_to_gguf():
    convert_script = "/mnt/linux-data/project/code/models/llama.cpp/convert.py"
    model_dir = "/mnt/linux-data/project/code/models/merged_model"
    output_dir = "/mnt/linux-data/project/code/models/gguf"

    print("🔁 Converting to GGUF...")
    os.makedirs(output_dir, exist_ok=True)
    subprocess.run([
        "python", convert_script,
        "--outfile", f"{output_dir}/nous-hermes-parser.gguf",
        "--outtype", "q4_k_m",
        "--vocab-type", "bpe",
        model_dir
    ], check=True)
    print("✅ GGUF conversion complete.")

# === MAIN ===
if __name__ == "__main__":
    download_base_model()
    run_finetuning()
    merge_lora()
    convert_to_gguf()
