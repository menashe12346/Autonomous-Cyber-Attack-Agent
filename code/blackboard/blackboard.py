import copy
from config import DEFAULT_STATE_STRUCTURE

def initialize_blackboard(target_ip: str = ""):
    blackboard = copy.deepcopy(DEFAULT_STATE_STRUCTURE)
    if target_ip:
        try:
            blackboard["target"]["ip"] = target_ip
        except KeyError:
            pass
    return blackboard