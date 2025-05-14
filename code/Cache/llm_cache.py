import os
import json
from typing import Dict, Any, List
from config import LLM_CACHE_PATH


class LLMCache:
    """
    Flexible LLM cache: supports nested category trees.
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

    def _split_key(self, key: str) -> (str, List[str]):
        parts = key.split("::")
        return parts[0], parts[1:]  # action, path

    def get(self, key: str) -> Any:
        """
        תמיד טוען מחדש את הקובץ מהדיסק, כדי לוודא שהמידע מעודכן.
        תומך במפתחות מקוננים: action::category1::category2::...
        """
        self.cache = self._load_cache()  # קריאה תמידית מהקובץ

        base_action, path = self._split_key(key)
        for entry in self.cache:
            if entry["action"] == base_action:
                node = entry.get("categories", {})
                for part in path:
                    if isinstance(node, dict) and part in node:
                        node = node[part]
                    else:
                        return None
                return node
        return None

    def set(self, key: str, value: Any) -> None:
        base_action, path = self._split_key(key)
        if not path:
            print("[!] Cannot set cache without at least one category (use action::category)")
            return

        # חפש או צור entry לפי base_action
        for entry in self.cache:
            if entry["action"] == base_action:
                node = entry.setdefault("categories", {})
                for part in path[:-1]:
                    node = node.setdefault(part, {})
                node[path[-1]] = value
                self._save_cache()
                return

        # אם אין כניסה בכלל לאקשן
        node = {}
        current = node
        for part in path[:-1]:
            current[part] = {}
            current = current[part]
        current[path[-1]] = value

        self.cache.append({
            "action": base_action,
            "categories": node
        })
        self._save_cache()

    def debug_print(self):
        print("\n=== Cache Entries ===")
        for entry in self.cache:
            print(f"Action: {entry['action']}")
            print(json.dumps(entry.get("categories", {}), indent=2, ensure_ascii=False))
            print("---------------------")
        print("======================\n")
