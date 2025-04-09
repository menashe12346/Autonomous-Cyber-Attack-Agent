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

    def encode(self, state: dict, actions_history: list) -> torch.Tensor:
        """
        ממיר את מילון ה־state + היסטוריית פקודות לווקטור Torch עקבי.
        כל פעולה מקודדת לפי אינדקס בפעולות האפשריות (action_space).
        """
        # יצירת hash לזיהוי מצב
        state_str = json.dumps(state, sort_keys=True, separators=(',', ':'))
        state_hash = hashlib.sha256(state_str.encode()).hexdigest()
        self.encoded_to_state[state_hash] = state

        # שלב 1: קידוד ה־state עצמו
        flat_state = self._flatten_state(state)

        # שלב 2: קידוד היסטוריית פעולות לפי action_to_index
        actions_vector = np.zeros(len(self.action_space), dtype=np.float32)
        for action in actions_history:
            if action in self.action_to_index:
                idx = self.action_to_index[action]
                actions_vector[idx] = 1.0

        # הוספת הפקודות המקודדות ל־flat_state
        for i, val in enumerate(actions_vector):
            flat_state[f"action_history_idx_{i}"] = val

        # שלב 3: מיון, נורמליזציה ויצירת וקטור
        sorted_items = sorted(flat_state.items())
        encoded_values = [self._normalize_value(k, v) for k, v in sorted_items]

        # ריפוד או קיצוץ
        if len(encoded_values) < self.max_features:
            encoded_values += [0.0] * (self.max_features - len(encoded_values))
        else:
            encoded_values = encoded_values[:self.max_features]

        vector = torch.tensor(encoded_values, dtype=torch.float32)
        print(f"[Encoder] Encoded vector of length {len(encoded_values)} (state + history)")
        return vector

    def decode(self, state_hash: str) -> dict:
        """
        מחזיר את מצב ה-Blackboard המקורי לפי ה-hash שנשמר.
        """
        return self.encoded_to_state.get(state_hash, {})

    def _flatten_state(self, obj, prefix='') -> dict:
        """
        הופך מבנה מקונן (dict/list) למילון שטוח של feature_name → numeric_value.
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
            # הפיכת מחרוזת לערך מספרי קבוע בטווח
            hash_val = int(hashlib.sha256(obj.encode()).hexdigest(), 16) % 10**6
            items[prefix] = float(hash_val)
        else:
            items[prefix] = 0.0
        return items

    def _normalize_value(self, key: str, value: float) -> float:
        """
        נורמליזציה של ערכים לפי מאפיינים ידועים. אם לא זוהה – מחזיר כפי שהוא.
        """
        if "port" in key or "services" in key or "commands" in key:
            return min(value / 100.0, 1.0)
        elif "detected" in key or "shell" in key or "opened" in key:
            return min(value, 1.0)
        elif "reward" in key:
            return max(min(value / 10.0, 1.0), -1.0)
        else:
            return min(value / 1000.0, 1.0)
