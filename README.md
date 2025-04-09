# ╔════════════════════════════════════════════════════╗
# ║        🚀 SETUP & RUN LLAMA.CPP WITH NOUS-HERMES  ║
# ╚════════════════════════════════════════════════════╝

# ─────────────────────────────────────────────
# 📦 1. INSTALL DEPENDENCIES (CHOOSE YOUR OS)
# ─────────────────────────────────────────────

# 👉 For Arch Linux:
sudo pacman -Syu --needed base-devel cmake git python-pip

# 👉 For Ubuntu/Debian:
sudo apt update && sudo apt install -y build-essential cmake git python3-pip
pip install huggingface_hub

# ─────────────────────────────────────────────
# 📥 2. DOWNLOAD THE MODEL (.GGUF FORMAT)
# ─────────────────────────────────────────────

# (Optional) Login to HuggingFace if the model is gated:
huggingface-cli login   # ← Paste your token when prompted

# 📄 Download the model file:
wget -P ./ \
https://huggingface.co/NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF/resolve/main/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf

# ─────────────────────────────────────────────
# 🛠️ 3. CLONE AND BUILD LLAMA.CPP
# ─────────────────────────────────────────────

git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake ..
cmake --build . --config Release -j$(nproc)

# ─────────────────────────────────────────────
# ✅ 4. RUN THE MODEL WITH A TEST PROMPT
# ─────────────────────────────────────────────

# Replace <model_path> if needed:
./bin/llama-run ../Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf "Hello! What is 2 + 2?"
