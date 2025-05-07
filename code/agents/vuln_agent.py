import json
import re
import fnmatch
import sys
import os
import orjson

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import TARGET_IP, LLAMA_RUN, MODEL_PATH, CVE_PATH
from agents.base_agent import BaseAgent

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

    def __init__(self, blackboard_api, cve_items, epsilon, os_linux_dataset, os_linux_kernel_dataset):
        super().__init__(
            name="VulnAgent",
            action_space=[],  # No actions
            blackboard_api=blackboard_api,
            replay_buffer=None,
            policy_model=None,
            state_encoder=None,
            action_encoder=None,
            command_cache={},
            model=None,
            epsilon=epsilon,
            os_linux_dataset=os_linux_dataset,
            os_linux_kernel_dataset=os_linux_kernel_dataset
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
        self.blackboard_api.blackboard["cpes"] = possible_cpes

        found_vulns = self.filter_top_vulnerabilities(found_vulns)
        self.blackboard_api.blackboard["vulnerabilities_found"] = found_vulns
        print(f"[VulnAgent] Final selected top {len(found_vulns)} vulnerabilities:")
        self.blackboard_api._save_to_file()
    
    def filter_top_vulnerabilities(self, matches, top_n=900):
        """
        Filters the top N vulnerabilities by CVSS base score (v3 if available).
        """
        def get_score(cve_id):
            try:
                item = next((entry for entry in self.cve_items if entry["cve"]["CVE_data_meta"]["ID"] == cve_id), None)
                if not item:
                    return 0
                metrics = item.get("impact", {}).get("baseMetricV3", {})
                return metrics.get("cvssV3", {}).get("baseScore", 0)
            except:
                return 0

        enriched = [(match, get_score(match["cve"])) for match in matches]
        enriched.sort(key=lambda x: x[1], reverse=True)
        return [entry[0] for entry in enriched[:top_n]]

    def match_cves_to_cpes(self, possible_cpes):
        """
        Compare possible CPEs from current state to CVE database and return matching entries.
        Now matches purely on the product slot (parts[4] of cpe23Uri) vs. detected services.
        """
        vuln_dict = {}

        # build set of detected service names, e.g. {"apache","mysql","vsftpd"}
        service_names = {
            s.get("service", "").strip().lower()
            for s in self.blackboard_api.get_state_for_agent(self.name)
                         .get("target", {})
                         .get("services", [])
        }

        for item in self.cve_items:
            try:
                cve_id = item["cve"]["CVE_data_meta"]["ID"]
                nodes  = item.get("configurations", {}).get("nodes", [])
                impact = item.get("impact", {})

                # pre-calc CVSS
                if "baseMetricV3" in impact:
                    cvss = impact["baseMetricV3"]["cvssV3"].get("baseScore", 0.0)
                elif "baseMetricV2" in impact:
                    cvss = impact["baseMetricV2"]["cvssV2"].get("baseScore", 0.0)
                else:
                    cvss = 0.0

                for node in nodes:
                    for match in extract_all_cpe_matches(node):
                        uri_parts = match.get("cpe23Uri", "").lower().split(":")
                        # cpe:2.3:<part>:<vendor>:<product>:...
                        if len(uri_parts) < 5:
                            continue
                        product = uri_parts[4]
                        if product in service_names:
                            vuln_dict.setdefault(cve_id, {
                                "cve": cve_id,
                                "matched_cpes": [],
                                "cvss": cvss
                            })["matched_cpes"].append(match.get("cpe23Uri"))
                            # once we’ve counted this CVE, move to next CVE
                            raise StopIteration

            except StopIteration:
                continue
            except Exception as e:
                print(f"[!] Failed parsing CVE {cve_id}: {e}")
                continue

        return list(vuln_dict.values())
            
    def generate_possible_cpes(self, state_dict):
        target = state_dict.get("target", {})
        cpes = set()

        # === OS to CPE ===
        os_info = target.get("os", {})
        # אם יש גרסה בדיסט’ או בארכיטקטורה, אפשר להוסיף פה גרסה קבועה
        distro = os_info.get("distribution", {})
        if distro.get("name"):
            name = distro["name"].strip().lower().replace(" ", "_")
            # wildcard
            cpes.add(f"cpe:2.3:o:{name}:{name}:*:*:*:*:*:*:*:*")
            # version-pinned אם ידוע
            if distro.get("version"):
                ver = distro["version"].strip().lower().replace(" ", "_")
                cpes.add(f"cpe:2.3:o:{name}:{name}:{ver}:*:*:*:*:*:*:*:*")

        # === Services to CPE ===
        for s in target.get("services", []):
            name = s.get("service", "").strip().lower().replace(" ", "_")
            version = s.get("server_version", "").strip().lower()
            if not name:
                continue

            # 1) התבניות הג׳נריות שלך
            for cpe in self._generate_service_cpes(name, name):
                cpes.add(cpe)

            # 2) תבנית עם גרסה קבועה
            if version:
                # אפשר גם wildcard ב־vendor או ב־product אם רוצים
                cpes.add(f"cpe:2.3:a:{name}:{name}:{version}:*:*:*:*:*:*:*:*")

        # === Web Directories Heuristics ===
        dirs = state_dict.get("web_directories_status", {})
        cpes |= {
            cpe
            for code in ("200", "403")
            for path in dirs.get(code, {})
            if (dir_name := path.strip("/").lower()) and "/" not in dir_name
            for cpe in self._generate_service_cpes(
                dir_name.replace("-", "_"), dir_name.replace("-", "_")
            )
        }

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
