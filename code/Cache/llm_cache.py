import hashlib
import json
import os
import pickle

class LLMCache:
    def __init__(self, cache_file="llm_cache.pkl"):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_cache(self):
        with open(self.cache_file, "wb") as f:
            pickle.dump(self.cache, f)

    def _hash(self, state, action):
        data = {
            "state": state,
            "action": action
        }
        state_action_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(state_action_str.encode()).hexdigest()

    def get(self, state, action):
        key = self._hash(state, action)
        return self.cache.get(key)

    def set(self, state, action, value):
        key = self._hash(state, action)
        self.cache[key] = value
        self._save_cache()