from config import DEFAULT_TARGET_STRUCTURE, DEFAULT_WEB_DIRECTORIES_STATUS

def initialize_blackboard(target_ip: str = ""):
    blackboard = {}
    initialize_target(blackboard, target_ip)
    initialize_web_directories_status(blackboard)
    return blackboard

def initialize_target(blackboard, target_ip):
    blackboard["target"] = DEFAULT_TARGET_STRUCTURE.copy()
    blackboard["target"]["ip"] = target_ip or ""

def initialize_web_directories_status(blackboard):
    blackboard["web_directories_status"] = DEFAULT_WEB_DIRECTORIES_STATUS.copy()
