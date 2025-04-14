# Simulation parameters
NUM_EPISODES = 100
MAX_STEPS_PER_EPISODE = 5

# Target configuration
TARGET_IP = "192.168.56.101"

# Model configuration
LLAMA_RUN = "/mnt/linux-data/project/code/models/llama.cpp/build/bin/llama-run"
MODEL_PATH = "file:///mnt/linux-data/project/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"

# Wordlists paths
WORDLISTS = {
    "gobuster_common": "/mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt"
}

# LLM cache path
LLM_CACHE_PATH = "/mnt/linux-data/project/code/Cache/llm_cache.pkl"