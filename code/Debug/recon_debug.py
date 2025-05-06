from copy import deepcopy
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import STATE_SCHEMA
# עזר: פונקציה לחילוץ ערכים מקונסטרוקציות מקוננות
def get_nested(d, path):
    keys = path.replace("[]", "").split(".")
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, {})
        else:
            return None
    return d

# סכמת דוגמה פשוטה
STATE_SCHEMA = {
    "target.os.name": {
        "type": "string",
        "reward": 0.1,
        "encoder": "base100_encode"
    },
    "target.services[].service": {
        "type": "string",
        "reward": 0.2,
        "encoder": "base100_encode"
    },
    "web_directories_status.200": {
        "type": "dict",
        "reward": 0.05,
        "encoder": "count_encoder"
    }
}

def traverse_schema_key(data, key_parts):
        """
        Recursively retrieves all values pointed to by the schema key parts.
        Supports nested dicts and lists (using '[]' to indicate lists).

        Args:
            data (dict or list): The current level of the data to examine.
            key_parts (list): List of key parts from a parsed schema key.

        Returns:
            list: All values reached by traversing the key parts.
        """
        if not key_parts:
            return [data]

        current = key_parts[0]
        rest = key_parts[1:]

        results = []

        if isinstance(data, dict):
            if current.endswith("[]"):
                list_key = current[:-2]
                sublist = data.get(list_key, [])
                if isinstance(sublist, list):
                    for item in sublist:
                        results.extend(traverse_schema_key(item, rest))
            else:
                next_data = data.get(current)
                if next_data is not None:
                    results.extend(traverse_schema_key(next_data, rest))

        elif isinstance(data, list):
            for item in data:
                results.extend(traverse_schema_key(item, key_parts))

        return results

# דוגמה למחלקה בודקת עם get_reward
class DummyAgent:
    def __init__(self):
        self.actions_history = []
        self.state_encoder = type("DummyEncoder", (), {"schema": STATE_SCHEMA})()
        self.prev_state = {}

    def get_reward(self, prev_dict: dict, action: str, next_dict: dict) -> float:
        """
        מחשבת תגמול כללי לפי STATE_SCHEMA:
        - תגמול עבור גילוי שדות חדשים בהתאם ל-reward שב-schema
        - תגמול על שירותים חדשים כקבוצה (tuple של port, protocol, service)
        - עונש על חזרה על פעולה
        - עונש אם לא התגלה כלום
        """
        reward = 0.0
        reasons = []

        schema = self.state_encoder.schema

        # 1) חזרה על פעולה / פעולה ראשונה
        if action in self.actions_history:
            count = self.actions_history.count(action)
            penalty = -0.5 * count
            reward += penalty
            reasons.append(f"Action repeated {count} times {penalty:+.1f}")
        else:
            reward += 0.1
            reasons.append("First time action +0.1")

        # 1.a) תגמול על שירותים חדשים (tuple של port, protocol, service)
        prev_svcs = get_nested(prev_dict, "target.services") or []
        next_svcs = get_nested(next_dict, "target.services") or []
        prev_set = {
            (s.get("port", ""), s.get("protocol", ""), s.get("service", ""))
            for s in prev_svcs if isinstance(s, dict)
        }
        next_set = {
            (s.get("port", ""), s.get("protocol", ""), s.get("service", ""))
            for s in next_svcs if isinstance(s, dict)
        }
        new_services = next_set - prev_set
        if new_services:
            svc_weight = schema.get("target.services[].service", {}).get("reward", 0)
            total = svc_weight * len(new_services)
            reward += total
            reasons.append(f"Discovered {len(new_services)} new services +{total:.2f}")

        # 2) מעבר על שדות אחרים בסכמה
        for raw_key, meta in schema.items():
            # דילוג על טיפול בשירותים – כבר טופל למעלה
            if raw_key.startswith("target.services[]"):
                continue

            weight = meta.get("reward", 0.0)
            if weight <= 0:
                continue

            encoder = meta.get("encoder", "")

            # A) count_encoder: ספירת פריטים בהבדל
            if encoder == "count_encoder":
                prev_container = get_nested(prev_dict, raw_key) or {}
                next_container = get_nested(next_dict, raw_key) or {}
                try:
                    prev_count = len(prev_container)
                    next_count = len(next_container)
                except Exception:
                    continue
                diff = next_count - prev_count
                if diff > 0:
                    total = weight * diff
                    reward += total
                    reasons.append(
                        f"Discovered {diff} new items under {raw_key} +{total:.2f}"
                    )
                continue

            # B) list-element fields: raw_key contains "[]"
            if "[]" in raw_key:
                parts = raw_key.split("[].")
                if len(parts) < 2:
                    continue
                prefix = "[].".join(parts[:-1])
                field = parts[-1]

                prev_list = get_nested(prev_dict, prefix) or []
                next_list = get_nested(next_dict, prefix) or []

                prev_vals = {
                    str(item.get(field, "")).strip()
                    for item in prev_list if isinstance(item, dict)
                }
                next_vals = {
                    str(item.get(field, "")).strip()
                    for item in next_list if isinstance(item, dict)
                }
                new_vals = next_vals - prev_vals
                if new_vals:
                    total = weight * len(new_vals)
                    reward += total
                    reasons.append(
                        f"Discovered {len(new_vals)} new '{field}' under {prefix} +{total:.2f}"
                    )
                continue

            # C) שדות רגילים (string / number)
            prev_val = str(get_nested(prev_dict, raw_key) or "").strip()
            next_val = str(get_nested(next_dict, raw_key) or "").strip()
            if not prev_val and next_val:
                reward += weight
                reasons.append(f"Discovered {raw_key} = '{next_val}' +{weight:.2f}")

        # 3) עונש אם לא התגלה כלום (מלבד repeat/first-time ושירותים)
        if len(reasons) == 1:
            reward -= 1.0
            reasons.append("No new fields discovered -1.0")

        # Debug
        print("\n[Reward Debug]")
        print(f"Action: {action}")
        for r in reasons:
            print("  ", r)
        print(f"Total raw reward: {reward:.2f}\n")

        # 4) עדכון היסטוריה
        self.actions_history.append(action)
        self.prev_state = dict(next_dict)

        return reward



# הדוגמה בפועל
if __name__ == "__main__":
    agent = DummyAgent()

    prev_state = {
        "target": {
            "os": {
                "name": ""
            },
            "services": []
        },
        "web_directories_status": {
            "200": {
                "/old": "",
                "/123": ""

            }
        }
    }

    next_state = deepcopy(prev_state)
    next_state["target"]["os"]["name"] = "linux"
    next_state["target"]["services"] = [{"port": "80", "protocol": "tcp", "service": "http"}]
    next_state["web_directories_status"]["200"]["/admin"] = ""
    next_state["web_directories_status"]["200"]["/1234"] = ""


    action = "nmap 192.168.56.101"

    reward = agent.get_reward(prev_state, action, next_state)
    print(f"Reward: {reward}")
