import os
import pickle

from config import COMMAND_LLM_PATH

class CommandLLMCache:
    """
    Caches LLM outputs based either on command input or command output.
    """

    def __init__(self, cache_file=COMMAND_LLM_PATH, use_input_instead_of_output=True):
        self.cache_file = cache_file
        self.use_input_instead_of_output = use_input_instead_of_output
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "wb") as f:
            pickle.dump(self.cache, f)

    def _get_key(self, command_input_or_output):
        """
        Generates a unique key based on the configuration: 
        using input or output.
        """
        return command_input_or_output.strip()

    def get(self, command_input_or_output):
        """
        Retrieves a cached result based on the command input/output.
        """
        key = self._get_key(command_input_or_output)
        return self.cache.get(key)

    def set(self, command_input_or_output, value):
        """
        Stores a result in the cache for a specific command input/output.
        """
        key = self._get_key(command_input_or_output)
        self.cache[key] = value
        self._save_cache()
