# Project path
PROJECT_PATH = "/mnt/linux-data"

# Simulation parameters
NUM_EPISODES = 100
MAX_STEPS_PER_EPISODE = 4

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
LLM_CACHE_PATH = f"{PROJECT_PATH}/project/code/Cache/llm_cache.json"

# command LLM cache path
COMMAND_LLM_PATH = f"{PROJECT_PATH}/project/code/Cache/command_llm_cache.pkl"

# NVD cve dataset path
CVE_PATH = f"{PROJECT_PATH}/project/code/datasets/nvd_files/nvd_cve_dataset.json"

# Blackboard path
BLACKBOARD_PATH = f"{PROJECT_PATH}/project/code/blackboard/blackboard.json"

# NVD files path
NVD_CVE_PATH = f"{PROJECT_PATH}/project/code/datasets/nvd_files/"

# Datasets path
DATASETS_PATH = f"{PROJECT_PATH}/project/code/datasets"

# ExploitDB dataset path
CVE_EXPLOIT_PATH = f"{PROJECT_PATH}/project/code/datasets/exploitdb/cve_exploit_dataset.csv"

# ExploitDB files exploits
EXPLOITDB_FILES_EXPLOITS_PATH = f"{PROJECT_PATH}/project/code/datasets/exploitdb/files_exploits.csv"

# ExploitDB dataset
EXPLOITDB_DATASET_PATH = f"{PROJECT_PATH}/project/code/datasets/exploitdb/cve_exploit_dataset.csv"

# Metasploit dataset
METASPLOIT_DATASET = f"{PROJECT_PATH}/project/code/datasets/metasploit/metasploit_dataset.json"

# Metasploit path
METASPLOIT_PATH = f"{PROJECT_PATH}/project/code/datasets/metasploit/metasploit-framework"

EXPLOIT_DATASET = f"{PROJECT_PATH}/project/code/datasets/exploit_datasets/full_exploit_dataset.json"

OS_LINUX_DATASET= f"{PROJECT_PATH}/project/code/datasets/os_datasets/os_linux_dataset.json"

OS_LINUX_KERNEL_DATASET = f"{PROJECT_PATH}/project/code/datasets/os_datasets/os_linux_kernel_dataset.json"

TEMPORARY_DISTROWATCH_FILES = f"{PROJECT_PATH}/project/code/datasets/os_datasets/temporary_DistroWatch_files"

DISTROWATCH_FILES =  f"{PROJECT_PATH}/project/code/datasets/os_datasets/DistroWatch_files"

OS_DATASETS = f"{PROJECT_PATH}/project/code/datasets/os_datasets"

CORRECTNESS_CACHE = f"{PROJECT_PATH}/project/code/Cache/correctness_cache.json"

# STATE CONFIGURATION #

# סטטוסים מצופים לדפי Web
EXPECTED_STATUS_CODES = [
    "200", "301", "302", "307", "401", "403", "500", "502", "503", "504"
]

# שמרו את התבנית הבסיסית בשדה פנימי
_BASE_DEFAULT_STATE = {
    "target": {
        "ip": "",
        "os": {
            "name": "",
            "distribution": {"name": "", "version": ""},
            "kernel": "",
            "architecture": ""
        },
        "services": [
            {"port": "", "protocol": "", "service": ""},
            {"port": "", "protocol": "", "service": ""},
            {"port": "", "protocol": "", "service": ""}
        ]
    },
    "web_directories_status": {code: {"": ""} for code in EXPECTED_STATUS_CODES}
}

import copy

def __getattr__(name):
    if name == "DEFAULT_STATE_STRUCTURE":
        # כל גישה ל־DEFAULT_STATE_STRUCTURE מחזירה עותק עומק חדש
        return copy.deepcopy(_BASE_DEFAULT_STATE)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")