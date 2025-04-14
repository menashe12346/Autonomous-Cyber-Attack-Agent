import os
import pickle

from config import LLM_CACHE_PATH

class LLMCache:
    """
    Caches LLM outputs to avoid redundant processing for identical state-action pairs.
    """

    def __init__(self, cache_file=LLM_CACHE_PATH, state_encoder=None):
        self.cache_file = cache_file
        self.state_encoder = state_encoder
        self.cache = self._load_cache()

    def _load_cache(self):
        """
        Loads the cache from disk if it exists.
        """
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_cache(self):
        """
        Saves the current cache dictionary to disk.
        """
        with open(self.cache_file, "wb") as f:
            pickle.dump(self.cache, f)

    def _get_key(self, state_dict, actions_history, action_str):
        """
        Generates a unique key for the cache based on:
        - the encoded state (including action history)
        - the current action string
        """
        vector = self.state_encoder.encode(state_dict, actions_history)
        vector_key = str(vector.tolist())
        return f"{vector_key}||{action_str}"

    def get(self, state_dict, action_str, actions_history=[]):
        """
        Retrieves a cached result based on the state, history, and action.
        Returns None if no cached result exists.
        """
        key = self._get_key(state_dict, actions_history, action_str)
        return self.cache.get(key)

    def set(self, state_dict, action_str, value, actions_history=[]):
        """
        Stores a result in the cache for a specific state and action.
        """
        key = self._get_key(state_dict, actions_history, action_str)
        self.cache[key] = value
        self._save_cache()