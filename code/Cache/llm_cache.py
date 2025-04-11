import os
import pickle

class LLMCache:
    def __init__(self, cache_file="llm_cache.pkl", state_encoder=None):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.state_encoder = state_encoder

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_cache(self):
        with open(self.cache_file, "wb") as f:
            pickle.dump(self.cache, f)

    def _get_key(self, state_dict, actions_history, action_str):
        """
        מקודד את המצב + היסטוריה → וקטור → מחרוזת → מחבר עם פעולה
        """
        vector = self.state_encoder.encode(state_dict, actions_history)
        vector_key = str(vector.tolist())
        return f"{vector_key}||{action_str}"

    def get(self, state_dict, action_str, actions_history=[]):
        key = self._get_key(state_dict, actions_history, action_str)
        return self.cache.get(key)

    def set(self, state_dict, action_str, value, actions_history=[]):
        key = self._get_key(state_dict, actions_history, action_str)
        self.cache[key] = value
        self._save_cache()