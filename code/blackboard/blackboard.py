import copy
from config import DEFAULT_STATE_STRUCTURE

def initialize_blackboard(target_ip: str = ""):
    """
    יוצר את מבנה ה־blackboard על פי המבנה המוגדר בקונפיג.
    ממלא את כתובת ה־IP אם ניתנה.
    """
    blackboard = copy.deepcopy(DEFAULT_STATE_STRUCTURE)
    if target_ip:
        try:
            blackboard["target"]["ip"] = target_ip
        except KeyError:
            pass  # במידה ו־"target" לא מוגדר – מתעלמים
    return blackboard