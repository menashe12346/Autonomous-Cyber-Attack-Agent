# 🚀 Installing Dependencies & Running `llama.cpp` with Nous-Hermes Model

# =====================================
# 📦 Install Dependencies (Choose OS)
# =====================================

# For Arch Linux:
sudo pacman -Syu --needed base-devel cmake git python-pip

# For Ubuntu/Debian:
sudo apt update && sudo apt install -y build-essential cmake git python3-pip
pip install huggingface_hub

# =====================================
# 📥 Download the Model
# =====================================

# (Optional) Login to HuggingFace if the model is gated:
huggingface-cli login  # paste your token when prompted

# Download model manually to current directory (or change path as needed):
wget -P ./ \
https://huggingface.co/NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF/resolve/main/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf

# =====================================
# 🛠️ Clone and Build llama.cpp
# =====================================

git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake ..
cmake --build . --config Release -j$(nproc)

# =====================================
# ✅ Run the model with a test prompt
# =====================================

# Replace <model_path> with the actual path to your .gguf file
./bin/llama-run ./../Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf "Hello! What is 2 + 2?"


 
