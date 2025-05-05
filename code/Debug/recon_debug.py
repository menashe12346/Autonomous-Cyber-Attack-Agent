from copy import deepcopy

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

# דוגמה למחלקה בודקת עם get_reward
class DummyAgent:
    def __init__(self):
        self.actions_history = []
        self.state_encoder = type("DummyEncoder", (), {"schema": STATE_SCHEMA})()
        self.prev_state = {}

    def get_reward(self, prev_dict, action, next_dict):
        # ... הדבק כאן את הפונקציה ששלחת ללא שינוי ...
        reward = 0.0
        reasons = []

        if action in self.actions_history:
            count = self.actions_history.count(action)
            penalty = -0.5 * count
            reward += penalty
            reasons.append(f"Action repeated {count} times {penalty:+.1f}")
        else:
            reward += 0.1
            reasons.append("First time action +0.1")

        schema = self.state_encoder.schema

        for raw_key, info in schema.items():
            weight = info.get("reward", 0)
            if weight <= 0:
                continue

            enc = info.get("encoder", "")

            if enc == "count_encoder":
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

            if "[]" in raw_key:
                prefix, field = raw_key.split("[].")
                prev_list = get_nested(prev_dict, prefix) or []
                next_list = get_nested(next_dict, prefix) or []
                prev_vals = {
                    str(item.get(field, "")).strip()
                    for item in prev_list
                    if isinstance(item, dict)
                }
                next_vals = {
                    str(item.get(field, "")).strip()
                    for item in next_list
                    if isinstance(item, dict)
                }
                new_vals = next_vals - prev_vals
                if new_vals:
                    total = weight * len(new_vals)
                    reward += total
                    reasons.append(
                        f"Discovered {len(new_vals)} new '{field}' under {prefix} +{total:.2f}"
                    )
                continue

            prev_val = str(get_nested(prev_dict, raw_key) or "").strip()
            next_val = str(get_nested(next_dict, raw_key) or "").strip()
            if not prev_val and next_val:
                reward += weight
                reasons.append(f"Discovered {raw_key} = '{next_val}' +{weight:.2f}")

        if len(reasons) == 1:
            reward -= 1.0
            reasons.append("No new fields discovered -1.0")

        print("\n[Reward Debug]")
        print(f"Action: {action}")
        for r in reasons:
            print("  ", r)
        print(f"Total raw reward: {reward:.2f}\n")

        self.prev_state = dict(next_dict)
        self.actions_history.append(action)

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
                "/old": ""
            }
        }
    }

    next_state = deepcopy(prev_state)
    next_state["target"]["os"]["name"] = "linux"
    next_state["target"]["services"] = [{"port": "80", "protocol": "tcp", "service": "http"}]
    next_state["web_directories_status"]["200"]["/admin"] = ""

    action = "nmap 192.168.56.101"

    reward = agent.get_reward(prev_state, action, next_state)
    print(f"Reward: {reward}")
