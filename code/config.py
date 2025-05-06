# Project path
PROJECT_PATH = "/mnt/linux-data"

# Simulation parameters
NUM_EPISODES = 1
MAX_STEPS_PER_EPISODE = 1
EPSILON = 0.6

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

RUN_MANUAL = f"{PROJECT_PATH}/project/code/run_manual.py"

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
            "distribution": {"name": "", "version": "", "architecture": ""},
            "kernel": "",
        },
        "services": [
            {
                "port": "", 
                "protocol": "", 
                "service": "", 
                "server_type": "", 
                "server_version": "",
                "supported_protocols": [""],
                "softwares": [
                    {"name": "", "version": ""},
                ]
            },
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

WEB_DIRECTORIES_STATUS_CODES_REWARD = {
    "200": 0.1,
    "301": 0.05,
    "302": 0.05,
    "307": 0.05,
    "401": 0.08,
    "403": 0.1,
    "500": 0.15,
    "502": 0.09,
    "503": 0.09,
    "504": 0.04
}

STATE_SCHEMA = {
    "target": {
        "type": "dict",
        "llm_prompt": False
    },
    "target.os": {
        "type": "dict",
        "correction_func": "correct_os"
    },
    "target.os.name": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "General operating system name, e.g., 'linux'."
    },
    "target.os.distribution.name": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "OS distribution name, e.g., 'ubuntu', 'debian'."
    },
    "target.os.distribution.version": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Version of the OS distribution, e.g., '20.04'."
    },
    "target.os.distribution.architecture": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "CPU architecture, e.g., 'x86', 'x64'."
    },
    "target.os.kernel": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "correction_func": "fix_os",
        "llm_prompt": "Kernel version string, e.g., '6.6.59'."
    },
    "target.services": {
        "type": "list",
        "correction_func": "correct_services",
        "llm_prompt": "An entry for each service found "
    },
    "target.services[].port": {
        "type": "int",
        "encoder": "normalize_by_specific_number",
        "num_for_normalization": 65536,
        "reward": 0.1,
        "llm_prompt": "Port number of the service, e.g., 22 or 80."
    },
    "target.services[].protocol": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0,
        "llm_prompt": "Transport protocol used by the service, e.g., 'tcp'."
    },
    "target.services[].service": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "Application-level service name, e.g., 'http', 'ftp'."
    },
    "target.services[].server_type": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].server_version": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].supported_protocols": {
        "type": "list",
        "llm_prompt": ""
    },
    "target.services[].supported_protocols[]": {
        "type": "str",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].softwares": {
        "type": "list",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].softwares[].name": {
        "type": "str",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].softwares[].version": {
        "type": "str",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "web_directories_status": {
        "type": "dict",
        "correction_func": "fix_web_status",
        "llm_prompt": f"For each status ({', '.join(EXPECTED_STATUS_CODES)}): discovered paths (like '/admin') to their message (or use \"\" if none), format: {{ \"path\": \"message\" }}."
    }
}

# Dynamic addition of status-specific entries
for status in EXPECTED_STATUS_CODES:
    STATE_SCHEMA[f"web_directories_status.{status}"] = {
        "type": "dict",
        "encoder": "count_encoder",
        "reward": WEB_DIRECTORIES_STATUS_CODES_REWARD[status]
    }
