# tinynet_trainer.py

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import random
from transformers import AutoTokenizer, AutoModel

# ========== CONFIG ==========
EMBEDDING_DIM = 384  # מבוסס על all-MiniLM-L6-v2
HIDDEN_DIM = 256
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TOKENIZER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_CACHE = {}

# ========== TOKENIZER & ENCODER ==========
tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_MODEL)
encoder_model = AutoModel.from_pretrained(TOKENIZER_MODEL).to(DEVICE)
encoder_model.eval()

def encode_text(text):
    print("[ENCODE] Encoding text to embedding vector...")
    with torch.no_grad():
        tokens = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
        outputs = encoder_model(**tokens)
        return outputs.last_hidden_state.mean(dim=1).squeeze(0).cpu().tolist()

def decode_embedding(embedding_vector):
    return "<decoded text unavailable without reverse mapping>"

# ========== MODEL ==========
class TinyNet(nn.Module):
    def __init__(self, input_dim=EMBEDDING_DIM, hidden_dim=HIDDEN_DIM, output_dim=EMBEDDING_DIM):
        super(TinyNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return self.fc2(x)

# ========== UTILITIES ==========
def mask_json(data):
    if isinstance(data, dict):
        return {k: mask_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_json(item) for item in data]
    else:
        return "<MASK>"

def load_dataset(path):
    print(f"[LOAD] Loading dataset from {path}...")
    with open(path, 'r') as f:
        return [json.loads(line.strip()) for line in f]

# ========== SAVE MODEL ==========
def save_model(model, path):
    print(f"[SAVE] Saving model to {path}...")
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    torch.save(model.state_dict(), path)

def load_model(model, path):
    print(f"[LOAD] Loading model from {path}...")
    model.load_state_dict(torch.load(path, map_location=DEVICE))
    return model

def structure_loss(predicted, target):
    return F.mse_loss(predicted, target)

# ========== DATASET GENERATOR ==========
def build_masked_dataset(examples, output_path):
    print(f"[BUILD] Building masked dataset to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        for ex in examples:
            prompt = ex["prompt"]
            raw_output = ex["output"]
            state = ex["state"]

            full_text = f"Prompt: {prompt}\nOutput: {raw_output}\nState: {json.dumps(state)}"
            input_vec = encode_text(full_text)
            masked_output = encode_text(json.dumps(mask_json(state)))

            item = {
                "input": input_vec,
                "masked_output": masked_output
            }
            f.write(json.dumps(item) + "\n")
    print("[BUILD] Done writing masked dataset.")

# ========== TRAINING LOOP ==========
def train_tinynet(model, dataset, model_path, epochs=10, lr=1e-4):
    if model_path in MODEL_CACHE:
        print("[CACHE] Loading model from cache...")
        model.load_state_dict(MODEL_CACHE[model_path])
    elif os.path.exists(model_path):
        model = load_model(model, model_path)
        MODEL_CACHE[model_path] = model.state_dict()

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()

    for epoch in range(epochs):
        total_loss = 0.0
        print(f"[TRAIN] Starting epoch {epoch+1}...")
        for i, example in enumerate(dataset):
            input_vec = torch.tensor(example['input'], dtype=torch.float32).to(DEVICE)
            target_vec = torch.tensor(example['masked_output'], dtype=torch.float32).to(DEVICE)

            output = model(input_vec)
            loss = structure_loss(output, target_vec)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

            if i % 10 == 0:
                print(f"  [BATCH {i}] Loss: {loss.item():.6f}")

        print(f"[TRAIN] Epoch {epoch+1}/{epochs} | Total Loss: {total_loss:.4f}")

    MODEL_CACHE[model_path] = model.state_dict()
    save_model(model, model_path)

# ========== TEST ==========
def test_tinynet(model, dataset):
    print("[TEST] Running evaluation on test set...")
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        for i, example in enumerate(dataset):
            input_vec = torch.tensor(example['input'], dtype=torch.float32).to(DEVICE)
            target_vec = torch.tensor(example['masked_output'], dtype=torch.float32).to(DEVICE)
            output = model(input_vec)
            loss = structure_loss(output, target_vec)
            total_loss += loss.item()
            if i % 10 == 0:
                print(f"  [TEST BATCH {i}] Loss: {loss.item():.6f}")
    avg_loss = total_loss / len(dataset)
    print(f"[TEST] Average Loss: {avg_loss:.6f}")


# ========== DATASET GENERATOR ==========
def build_masked_dataset(examples, output_path, raw_output_path=None):
    print(f"[BUILD] Building masked dataset to {output_path}...")
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if raw_output_path:
        print(f"[BUILD] Also saving raw dataset to {raw_output_path}...")
        raw_dir = os.path.dirname(raw_output_path)
        if raw_dir:
            os.makedirs(raw_dir, exist_ok=True)
        raw_file = open(raw_output_path, 'w')
    else:
        raw_file = None

    with open(output_path, 'w') as f:
        for ex in examples:
            prompt = ex["prompt"]
            raw_output = ex["output"]
            state = ex["state"]

            full_text = f"Prompt: {prompt}\nOutput: {raw_output}\nState: {json.dumps(state)}"
            input_vec = encode_text(full_text)
            masked_output = encode_text(json.dumps(mask_json(state)))

            item = {
                "input": input_vec,
                "masked_output": masked_output
            }
            f.write(json.dumps(item) + "\n")

            if raw_file:
                raw_file.write(json.dumps({"prompt": prompt, "output": raw_output, "state": state}) + "\n")

    if raw_file:
        raw_file.close()

    print("[BUILD] Done writing masked dataset.")

# ========== USAGE EXAMPLE ==========
if __name__ == "__main__":
    raw_examples = []
    print("[GEN] Generating artificial examples...")
    for i in range(20):
        ip = f"192.168.56.{random.randint(1, 254)}"
        ports = random.sample([22, 80, 443, 3306, 8080], k=2)
        prompt = f"nmap -sV {ip}"
        output = "\n".join([f"{p}/tcp open service_{p}" for p in ports])
        state = {
            "target": {
                "ip": ip,
                "os": "Linux",
                "services": []
            },
            "web_directories_status": {"404": {"": ""}, "200": {"": ""}, "403": {"": ""}, "401": {"": ""}, "503": {"": ""}},
            "actions_history": [],
            "cpes": [],
            "vulnerabilities_found": [],
            "failed_CVEs": []
        }
        raw_examples.append({"prompt": prompt, "output": output, "state": state})

    dataset_path = "nmap_masked.jsonl"
    raw_path = "nmap_raw.jsonl"
    model_save_path = "nmap.pt"

    build_masked_dataset(raw_examples, dataset_path, raw_output_path=raw_path)
    dataset = load_dataset(dataset_path)
    model = TinyNet().to(DEVICE)

    train_tinynet(model, dataset, model_save_path)
    test_tinynet(model, dataset)