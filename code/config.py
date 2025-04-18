# Project path
PROJECT_PATH = "/mnt/linux-data"

# Simulation parameters
NUM_EPISODES = 100
MAX_STEPS_PER_EPISODE = 5

# Target configuration
TARGET_IP = "192.168.56.101"

# Model configuration
LLAMA_RUN = f"{PROJECT_PATH}/project/code/models/llama.cpp/build/bin/llama-run"
MODEL_PATH = f"file://{PROJECT_PATH}/project/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"

# Wordlists paths
WORDLISTS = {
    "gobuster_common": f"{PROJECT_PATH}/wordlists/SecLists/Discovery/Web-Content/common.txt"
}

# LLM cache path
LLM_CACHE_PATH = f"{PROJECT_PATH}/project/code/Cache/llm_cache.pkl"

# NVD cve dataset path
CVE_PATH = f"{PROJECT_PATH}/project/code/datasets/nvd_files/nvd_cve_dataset.json"

# Blackboard path
BLACKBOARD_PATH = f"{PROJECT_PATH}/project/code/blackboard/blackboard.json"

# NVD files path
NVD_CVE_PATH = f"{PROJECT_PATH}/project/code/datasets/nvd_files/"