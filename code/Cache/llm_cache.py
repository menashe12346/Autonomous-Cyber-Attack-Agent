import os
import json
from typing import Dict, Any, List

from config import LLM_CACHE_PATH


class LLMCache:
    """
    Simple cache: stores action -> parsed result.
    """

    def __init__(self, cache_file: str = LLM_CACHE_PATH):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print("[!] Cache file is corrupted. Starting fresh.")
                    return []
        return []

    def _save_cache(self) -> None:
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def get(self, action: str) -> Any:
        """
        Looks for an exact action.
        Returns parsed result if found, else None.
        """
        for entry in self.cache:
            if entry["action"] == action:
                return entry["parsed"]
        return None

    def set(self, action: str, parsed: Any) -> None:
        """
        Saves a new (action, parsed) entry if it does not exist yet.
        """
        if not self.get(action):
            self.cache.append({
                "action": action,
                "parsed": parsed
            })
            self._save_cache()

    # [DEBUG]
    def debug_print(self):
        """
        Prints all entries in the cache for debugging.
        """
        print("\n=== Cache Entries ===")
        for entry in self.cache:
            print(f"Action: {entry['action']}")
            print(f"Parsed: {json.dumps(entry['parsed'], indent=2)}")
            print("---------------------")
        print("======================\n")
