import hashlib
import json
import torch
import numbers
import numpy as np

class StateEncoder:
    def __init__(self, action_space: list, max_features: int = 128):
        self.encoded_to_state = {}  # mapping hash → original state
        self.max_features = max_features  # גודל קבוע לווקטור הקלט
        self.action_space = action_space  # כל הפקודות האפשריות
        self.action_to_index = {action: i for i, action in enumerate(action_space)}

    def base100_encode(self, text: str) -> float:
        """
        מבצע קידוד מחרוזת לערך עשרוני בטווח [0, 1) לפי בסיס 100.
        """
        base = 100
        code = 0
        for i, c in enumerate(text[:5]):
            code += ord(c) * (base ** (4 - i))
        max_code = (base ** 5) - 1
        return code / max_code

    def encode(self, state: dict, actions_history: list) -> torch.Tensor:
        flat_state = self._flatten_state(state)

        actions_vector = np.zeros(len(self.action_space), dtype=np.float32)
        for action in actions_history:
            if action in self.action_to_index:
                idx = self.action_to_index[action]
                actions_vector[idx] = 1.0

        for i, val in enumerate(actions_vector):
            flat_state[f"action_history_idx_{i}"] = val

        sorted_items = sorted(flat_state.items())
        encoded_values = [self._normalize_value(k, v) for k, v in sorted_items]

        if len(encoded_values) < self.max_features:
            encoded_values += [0.0] * (self.max_features - len(encoded_values))
        else:
            encoded_values = encoded_values[:self.max_features]

        vector = torch.tensor(encoded_values, dtype=torch.float32)
        vector_key = str(vector.tolist())  # הפוך אותו למחרוזת ייחודית

        self.encoded_to_state[vector_key] = state  # שמור את המצב המקורי
        print(f"[Encoder] Encoded vector of length {len(encoded_values)} (state + history)")
        return vector

    def decode(self, vector_key: str) -> dict:
        return self.encoded_to_state.get(vector_key, {})

    def _flatten_state(self, obj, prefix='') -> dict:
        """
        הופך מבנה מקונן (dict/list) למילון שטוח של feature_name → numeric_value.
        כולל שימוש בקידוד base100 עבור מחרוזות.
        """
        items = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                items.update(self._flatten_state(v, full_key))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                full_key = f"{prefix}[{i}]"
                items.update(self._flatten_state(v, full_key))
        elif isinstance(obj, bool):
            items[prefix] = 1.0 if obj else 0.0
        elif isinstance(obj, numbers.Number):
            items[prefix] = float(obj)
        elif isinstance(obj, str):
            items[prefix] = self.base100_encode(obj)
        else:
            items[prefix] = 0.0
        return items

    def _normalize_value(self, key: str, value: float) -> float:
        """
        נורמליזציה של כל ערך למקטע [0, 1] לפי סוג המידע במפתח.
        """
        if isinstance(value, (int, float)):
            if "port" in key:
                return min(value / 65535.0, 1.0)
            elif "protocol" in key:
                return min(value / 3.0, 1.0)
            elif "action_history" in key:
                return float(value)
            elif "service" in key:
                return min(value / 1000000.0, 1.0)
            elif "web_directories_status" in key:
                return min(value / 1000000.0, 1.0)
            elif "os" in key:
                return min(value / 1000000.0, 1.0)
            else:
                return min(value / 1000000.0, 1.0)
        else:
            return 0.0
