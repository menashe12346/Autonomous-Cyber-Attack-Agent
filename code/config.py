# Main Directories paths
PROJECT_PATH = "/mnt/linux-data/project"
WORDLISTS_PATH = "/mnt/linux-data/wordlists"

# Main Directories inside the project
DATASETS_PATH = f"{PROJECT_PATH}/code/datasets"
DATABASES_PATH = f"{PROJECT_PATH}/code/databases"
OS_DATASETS = f"{DATASETS_PATH}/os_datasets"

# Simulation parameters
NUM_EPISODES = 1
MAX_STEPS_PER_EPISODE = 10
EPSILON = 0.6
MAX_ENCODING_FEATURES = 1024

# Target configuration
TARGET_IP = "192.168.56.101" 
# TARGET_IP = "146.190.62.39" 

# Wordlists paths
WORDLISTS = {
    "web_common": f"{WORDLISTS_PATH}/SecLists/Discovery/Web-Content/common.txt"
}

# LLM Model configuration
LLAMA_RUN_PATH = f"{PROJECT_PATH}/code/models/llama.cpp/build/bin/llama-run"
MISTRAL_MODEL_PATH = f"{PROJECT_PATH}/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"


# CACHE CONFIGURATION

# LLM cache path
LLM_CACHE_PATH = f"{PROJECT_PATH}/code/Cache/llm_cache.json"

# Command LLM cache path
COMMAND_LLM_CACHE_PATH = f"{PROJECT_PATH}/code/Cache/command_llm_cache.pkl"

# Correctness cache
CORRECTNESS_CACHE = f"{PROJECT_PATH}/code/Cache/correctness_cache.json"


# DATASETS CONFIGURATION

# NVD cve dataset path
DATASET_NVD_CVE_PATH = f"{DATASETS_PATH}/cve/nvd/nvd_cve_dataset.json"

# ExploitDB dataset path
DATASET_EXPLOITDB_CVE_EXPLOIT_PATH = f"{DATASETS_PATH}/exploitdb/exploitdb_dataset(cve,exploit_path).csv"

# ExploitDB files exploits
DATASET_EXPLOITDB_FILES_EXPLOITS_PATH = f"{DATASETS_PATH}/exploitdb/files_exploits.csv"

# Metasploit dataset
DATASET_METASPLOIT = f"{DATASETS_PATH}/metasploit/metasploit_dataset.json"

# Full exploit dataset
DATASET_EXPLOIT = f"{DATASETS_PATH}/exploit_datasets/full_exploit_dataset.json"

# OS Linux dataset
DATASET_OS_LINUX= f"{DATASETS_PATH}/os_datasets/os_linux_dataset.json"

# OS Linux kernel dataset
DATASET_OS_LINUX_KERNEL = f"{DATASETS_PATH}/os_datasets/os_linux_kernel_dataset.json"

#TEMPORARY_FILES

# NVD temporary files path
TEMPORARY_NVD_CVE_PATH = f"{DATASETS_PATH}/cve/nvd/temporary_nvd_files/"

# Temporary Distrowatch files
TEMPORARY_DISTROWATCH_FILES = f"{DATASETS_PATH}/os_datasets/DistroWatch_files/temporary_DistroWatch_files"


# OTHERS

# Distrowatch files
DISTROWATCH_FILES =  f"{PROJECT_PATH}/code/datasets/os_datasets/DistroWatch_files"

# Blackboard path
BLACKBOARD_PATH = f"{PROJECT_PATH}/code/blackboard/blackboard.json"


# STATE CONFIGURATION #

# Web Status codes
EXPECTED_STATUS_CODES = [
    "200", "301", "302", "307", "401", "403", "500", "502", "503", "504"
]

# Default state structure
_BASE_DEFAULT_STATE = {
    "target": {
        "hostname": "",
        "netbios_name": "",
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
        ],
        "rpc_services": [
            {
                "program_number": "",
                "version": "",
                "protocol": "",
                "port": "",
                "service_name": ""
            }
        ],
        "dns_records": [
            {"type": "", "value": ""},
        ],
        "network_interfaces": [
            {
                "name": "",
                "ip_address": "",
                "mac_address": "",
                "netmask": "",
                "gateway": ""
            }
        ],
        "geo_location": {
            "country": "",
            "region": "",
            "city": "",
        },
        "ssl": {
            "issuer": "",
            "protocols": [""],
        },
        "http_category": {
            "headers": {
                "Server": "",
                "X-Powered-By": "",
                "Content-Type": ""
            },
            "title": "",
            "robots_txt": "",
            "powered_by": ""
        },
        "trust_relationships": [
            {
                "source": "",
                "target": "",
                "type": "",
                "direction": "",
                "auth_type": ""
            }
        ],
        "users": [
            {
                "username": "",
                "group": "",
                "domain": "",
            },
        ],
        "groups": [""]
    },
    "web_directories_status": {code: {"": ""} for code in EXPECTED_STATUS_CODES}
}

import copy

# Making that every use of default stracture will be with deepcopy
def __getattr__(name):
    if name == "DEFAULT_STATE_STRUCTURE":
        return copy.deepcopy(_BASE_DEFAULT_STATE)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Web status codes reward
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

# state schema ( An explanation of the state). TODO: fix llm_prompt
STATE_SCHEMA = {
    "target": {
        "type": "dict",
        "llm_prompt": False
    },
    "target.netbios_name": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.hostaname": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.2,
        "llm_prompt": ""
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
    "target.os.distribution": {
        "type": "dict",
        "llm_prompt": ""
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
        "type": "string",
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
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].softwares[].version": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.rpc_services": {
        "type": "list",
        "correction_func": "correct_rpc_services",
        "llm_prompt": ""
    },
    "target.services[].program_number": {
        "type": "int",
        "encoder": "normalize_by_specific_number",
        "num_for_normalization": 999999,
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].version": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0,
        "llm_prompt": ""
    },
    "target.services[].protocol": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].port": {
        "type": "int",
        "encoder": "normalize_by_specific_number",
        "num_for_normalization": 999999,
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.services[].service_name": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.dns_records": {
        "type": "list",
        "correction_func": "correct_dns_records",
        "llm_prompt": ""
    },
    "target.dns_records[].type": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.dns_records[].value": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0,
        "llm_prompt": ""
    },
    "target.network_interfaces": {
        "type": "list",
        "correction_func": "correct_network_interfaces",
        "llm_prompt": ""
    },
    "target.network_interfaces[].name": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.network_interfaces[].ip_address": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.network_interfaces[].mac_address": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.network_interfaces[].netmask": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.network_interfaces[].gateway": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.geo_location": {
        "type": "dict",
        "llm_prompt": ""
    },
    "target.geo_location.country": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.geo_location.region": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.geo_location.city": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": ""
    },
    "target.ssl": {
        "type": "dict",
        "llm_prompt": ""
    },
    "target.ssl.issuer": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.ssl.protocols": {
        "type": "list",
        "llm_prompt": ""
    },
    "target.ssl.protocols[]": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": ""
    },
    "target.http_category": {
        "type": "dict",
        "llm_prompt": ""
    },
    "target.http_category.headers": {
        "type": "dict",
        "llm_prompt": ""
    },
    "target.http_category.headers.Server": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "Web server software name and version, e.g., 'Apache/2.4.41'."
    },
    "target.http_category.headers.X-Powered-By": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Technologies reported in the X-Powered-By header, e.g., 'PHP/7.4'."
    },
    "target.http_category.headers.Content-Type": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "MIME type of the HTTP response, e.g., 'text/html'."
    },
    "target.http_category.title": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Title of the web page as seen in the browser tab."
    },
    "target.http_category.robots_txt": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Contents of the robots.txt file if present."
    },
    "target.http_category.powered_by": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Technologies discovered in meta tags or HTTP headers, e.g., 'WordPress'."
    },

    "target.trust_relationships": {
        "type": "list",
        "llm_prompt": "List of trust relationships between systems or domains."
    },
    "target.trust_relationships[].source": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "The source system or domain in the trust relationship."
    },
    "target.trust_relationships[].target": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "The trusted system or domain in the relationship."
    },
    "target.trust_relationships[].type": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Type of trust relationship (e.g., 'one-way', 'transitive')."
    },
    "target.trust_relationships[].direction": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Direction of trust: 'inbound' or 'outbound'."
    },
    "target.trust_relationships[].auth_type": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Authentication method used in the trust (e.g., 'Kerberos')."
    },

    "target.users": {
        "type": "list",
        "llm_prompt": "List of discovered user accounts."
    },
    "target.users[].username": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.1,
        "llm_prompt": "Username of the account."
    },
    "target.users[].group": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Group the user belongs to, e.g., 'Administrators'."
    },
    "target.users[].domain": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Domain or hostname associated with the user account."
    },

    "target.groups": {
        "type": "list",
        "llm_prompt": "List of user groups on the system."
    },
    "target.groups[]": {
        "type": "string",
        "encoder": "base100_encode",
        "reward": 0.05,
        "llm_prompt": "Name of the group, e.g., 'Administrators', 'Users'."
    },

    "web_directories_status": {
        "type": "dict",
        "correction_func": "correct_web_directories",
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
