import time
import copy
import json
import re
from blackboard.utils import extract_json

class BlackboardAPI:
    def __init__(self, blackboard_dict: dict):
        self.blackboard = blackboard_dict

    def get_state_for_agent(self, agent_name: str) -> dict:
        """
        מחזיר את כל ה־Blackboard כפי שהוא, ללא סינון לפי סוג הסוכן.
        """
        return copy.deepcopy(self.blackboard)

    def update_runtime_behavior(self, info_dict: dict):
        """
        מעדכן את תת־המבנה 'runtime_behavior' עם המידע החדש שהתקבל מהפקודה.
        תומך בהוספת מפתחות חדשים או עדכון חכם של קיימים.
        """
        runtime = self.blackboard.setdefault("runtime_behavior", {})

        for key, value in info_dict.items():
            if isinstance(value, list):
                # אם זו רשימה, נאחד עם רשימה קיימת תוך הימנעות מכפולים
                existing = runtime.get(key, [])
                merged = list(set(existing + value))
                runtime[key] = merged
            elif isinstance(value, dict):
                # אם זה מבנה מקונן – נעשה עדכון רק ברמה אחת
                existing = runtime.get(key, {})
                if not isinstance(existing, dict):
                    existing = {}
                existing.update(value)
                runtime[key] = existing
            else:
                # ערכים פשוטים – פשוט לעדכן
                runtime[key] = value

    def append_action_log(self, entry: dict):
        """
        מוסיף רשומה ללוג הפעולות.
        """
        entry["timestamp"] = time.time()
        self.blackboard.setdefault("actions_log", []).append(entry)

    def record_reward(self, action: str, reward: float):
        """
        שומר את ערך התגמול לפעולה האחרונה שבוצעה.
        """
        entry = {
            "action": action,
            "reward": reward,
            "timestamp": time.time()
        }
        self.blackboard.setdefault("reward_log", []).append(entry)

    def add_error(self, agent: str, action: str, error: str):
        """
        מתעד שגיאה שהתרחשה במהלך הרצת פעולה.
        """
        entry = {
            "agent": agent,
            "action": action,
            "error": error,
            "timestamp": time.time()
        }
        self.blackboard.setdefault("errors", []).append(entry)

    def get_last_actions(self, agent: str, n: int = 5):
        """
        מחלץ את N הפעולות האחרונות שביצע סוכן מסוים.
        """
        return [
            log for log in reversed(self.blackboard.get("actions_log", []))
            if log["agent"] == agent
        ][:n]

    def update_target_services(self, new_services: list):
        """
        מוסיף שירותים חדשים ל־target.services אם הם עדיין לא קיימים.
        """
        existing = self.blackboard["target"].get("services", [])
        for service in new_services:
            if service not in existing:
                existing.append(service)

    def update_exploit_metadata(self, exploit_data: dict):
        """
        מעדכן את המידע על Exploit אחרון שנבחר.
        """
        self.blackboard["exploit_metadata"].update(exploit_data)

    def overwrite_blackboard(self, new_state: list):
        last_output = new_state[-1]

        if not isinstance(last_output, str):
            raise ValueError(f"❌ Model did not return a valid string output:\n{last_output}")

        parsed_json = extract_json(last_output)
        self.blackboard.clear()
        self.blackboard.update(parsed_json)