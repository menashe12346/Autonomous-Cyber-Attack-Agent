# ╔══════════════════════════════════════════════════════════╗
# ║       🚀 Setup & Run llama.cpp with Nous-Hermes          ║
# ╚══════════════════════════════════════════════════════════╝

# ────── 1. Install Dependencies (Choose your OS) ──────

# 👉 Arch Linux:
sudo pacman -Syu --needed base-devel cmake git python-pip

# 👉 Ubuntu / Debian:
sudo apt update && sudo apt install -y build-essential cmake git python3-pip
pip install huggingface_hub


# ────── 2. Clone the Project Repository ──────

git clone https://github.com/menashe12346/cyber_ai.git


# ────── 3. Download the Model (.gguf format) ──────

# Optional: Login to HuggingFace (if required)
huggingface-cli login  # ← Paste your token when asked

# Download model file into current directory:
wget -P ./ \
https://huggingface.co/NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF/resolve/main/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf


# ────── 4. Clone & Build llama.cpp ──────

git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake ..
cmake --build . --config Release -j$(nproc)


# ────── 5. Run the Model with a Prompt ──────

# Run with basic test input (adjust path if needed):
./bin/llama-run ../Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf "Hello! What is 2 + 2?"
