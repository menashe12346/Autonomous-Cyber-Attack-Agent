import json
import re
import fnmatch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import TARGET_IP, LLAMA_RUN, MODEL_PATH, CVE_PATH
from agents.base_agent import BaseAgent

def load_cve_database(cve_path: str):
    """
    Loads and normalizes the CVE database from the given JSON file.

    Returns:
        List[dict]: List of CVE items (parsed and ready).
    """
    with open(cve_path, "r", encoding="utf-8") as f:
        data = json.load(f)

        if isinstance(data, list):
            print("✅ CVE dataset Loaded successfully.")
            return data

        elif isinstance(data, dict) and "CVE_Items" in data:
            print("✅ CVE dataset Loaded successfully.")
            return data["CVE_Items"]

        else:
            raise ValueError("❌ Unsupported CVE format: expected list or dict with 'CVE_Items'")

def extract_all_cpe_matches(node):
    """
    Recursively extract all 'cpe_match' entries from a node and its children.
    """
    matches = []

    if "cpe_match" in node:
        matches.extend(node["cpe_match"])

    if "children" in node:
        for child in node["children"]:
            matches.extend(extract_all_cpe_matches(child))

    return matches
    
class VulnAgent(BaseAgent):
    """
    Agent that scans for CVEs matching known CPEs based on current state.
    """

    def __init__(self, blackboard_api, cve_items):
        super().__init__(
            name="VulnAgent",
            action_space=[],  # No actions
            blackboard_api=blackboard_api,
            replay_buffer=None,
            policy_model=None,
            state_encoder=None,
            action_encoder=None,
            command_cache={},
            model=None
        )
        self.cve_items = cve_items

    def should_run(self) -> bool:
        state = self.blackboard_api.get_state_for_agent(self.name)
        return True

    def get_reward(self, prev_state, action, next_state) -> float:
        return 0.0  # This agent does not learn

    def run(self):
        print("[+] VulnAgent running...")
        state = self.blackboard_api.get_state_for_agent(self.name)
        possible_cpes = self.generate_possible_cpes(state)

        found_vulns = self.match_cves_to_cpes(possible_cpes)

        print(f"[VulnAgent] Found {len(found_vulns)} matching CVEs")
        self.blackboard_api.blackboard["vulnerabilities_found"] = found_vulns

    def match_cves_to_cpes(self, possible_cpes):
        """
        Compare possible CPEs from current state to CVE database and return matching entries.
        Supports recursive search of cpe_match in nodes and nested children.
        """
        vuln_dict = {}

        for item in self.cve_items:
            try:
                cve_id = item["cve"]["CVE_data_meta"]["ID"]
                configurations = item.get("configurations", {})
                nodes = configurations.get("nodes", [])

                for node in nodes:
                    all_cpe_matches = extract_all_cpe_matches(node)

                    for match in all_cpe_matches:
                        match_cpe = match.get("cpe23Uri", "").lower()

                        for my_cpe in possible_cpes:
                            my_cpe = my_cpe.lower()

                            # התאמה רגילה עם תווים כלליים
                            if fnmatch.fnmatch(match_cpe, my_cpe):
                                vuln_dict.setdefault(cve_id, {"cve": cve_id, "matched_cpes": []})["matched_cpes"].append(match_cpe)
                                break

                            # התאמה לפי מילות מפתח בהקשר של HTTP
                            if "http" in my_cpe and "http" in match_cpe:
                                vuln_dict.setdefault(cve_id, {"cve": cve_id, "matched_cpes": []})["matched_cpes"].append(match_cpe)
                                break

            except Exception as e:
                print(f"[!] Failed parsing CVE {item.get('cve', {}).get('CVE_data_meta', {}).get('ID', 'unknown')}: {e}")
                continue

        return list(vuln_dict.values())

    def generate_possible_cpes(self, state_dict):
        """
        Generate all possible CPE 2.3 URIs from OS, services and web directories using a generic strategy.
        """
        cpes = set()
        target = state_dict.get("target", {})

        # === OS to CPE ===
        os_raw = target.get("os", "").strip().lower()
        if os_raw:
            vendor = os_raw.replace(" ", "_")
            product = os_raw.replace(" ", "_")
            cpes.add(f"cpe:2.3:o:{vendor}:{product}:*:*:*:*:*:*:*:*")

        # === Services to CPE ===
        services = target.get("services", [])
        for s in services:
            name = str(s.get("service", "")).strip().lower().replace(" ", "_")
            if not name:
                continue
            vendor = product = name
            cpes.update(self._generate_service_cpes(vendor, product))

        # === Web Directories Heuristics ===
        dirs = state_dict.get("web_directories_status", {})
        for code in ["200", "403"]:  # ננסה להוציא מזה מערכות קיימות
            paths = dirs.get(code, {})
            for path in paths:
                dir_name = path.strip("/").lower()
                if not dir_name or "/" in dir_name:
                    continue  # נתעלם מתיקיות ריקות או עמוקות מדי
                vendor = product = dir_name.replace("-", "_")
                cpes.update(self._generate_service_cpes(vendor, product))

        print(f"[VulnAgent] Generated {len(cpes)} possible CPEs (OS + Services + Web Heuristics).")
        return list(cpes)

    def _generate_service_cpes(self, vendor, product):
        """
        Helper to generate multiple flexible CPE patterns for a given vendor/product.
        """
        return {
            f"cpe:2.3:a:{vendor}:{product}:*:*:*:*:*:*:*:*",
            f"cpe:2.3:a:*:{product}:*:*:*:*:*:*:*:*",
            f"cpe:2.3:a:{vendor}:*:*:*:*:*:*:*:*:*"
        }

# DEBUG
if __name__ == "__main__":

    print("[*] Loading CVE database...")
    cve_items = load_cve_database(CVE_PATH)
    print(f"[+] Loaded {len(cve_items)} CVE entries")

    # מצב בדיקה ידני
    test_state = {
        "target": {
            "ip": "192.168.56.101",
            "os": "Linux",
            "services": [
                {"port": "80", "protocol": "tcp", "service": "apache"},
                {"port": "3306", "protocol": "tcp", "service": "mysql"}
            ]
        },
        "web_directories_status": {
            "200": {
                "/phpmyadmin/": "",
                "/dvwa/": ""
            },
            "403": {
                "/webdav/": ""
            }
        }
    }

    # מחלקת dummy כדי לדמות את ה-API
    class DummyBlackboardAPI:
        def get_state_for_agent(self, name):
            return test_state

        @property
        def blackboard(self):
            return {}

    # צור את הסוכן והפעל את הפונקציות
    agent = VulnAgent(blackboard_api=DummyBlackboardAPI(), cve_items=cve_items)

    possible_cpes = agent.generate_possible_cpes(test_state)
    matches = agent.match_cves_to_cpes(possible_cpes)

    print(f"\n[✓] Found {len(matches)} matching CVEs")
    for match in matches[:10]:  # מדפיס את 10 הראשונים בלבד
        print(f"  - {match['cve']}: {len(match['matched_cpes'])} matched CPEs")
        for cpe in match["matched_cpes"]:
            print(f"    • {cpe}")
