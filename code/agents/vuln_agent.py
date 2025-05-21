import json
import re
import fnmatch
import sys
import os
import orjson
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import DATASET_NVD_CVE_CPE_PATH  # ודא שאתה מייבא את זה

from config import DATASET_NVD_CVE_PATH, SERVICE_FAMILIES
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

    def __init__(self, blackboard_api, cve_items, epsilon, os_linux_dataset, os_linux_kernel_dataset, metasploit_dataset):
        super().__init__(
            name="VulnAgent",
            action_space=[],
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
        self.metasploit_dataset = metasploit_dataset

    def should_run(self) -> bool:
        state = self.blackboard_api.get_state_for_agent(self.name)
        return True

    def get_reward(self, prev_state, action, next_state) -> float:
        return 0.0  # This agent does not learn

    def run(self):
        print("[+] VulnAgent running...")
        state = self.blackboard_api.get_state_for_agent(self.name)
        possible_cpes = self.generate_possible_cpes(state)
        print(possible_cpes)
        found_vulns = self.match_cves_to_cpes(possible_cpes)
        print(found_vulns)

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
        Compare possible CPEs from current state to pre-parsed CVE-CPE mappings.
        Each entry in self.cve_items is a dict: {"cve": ..., "cpes": [...]}
        Matching is done by product name (part [4] in CPE URI) vs. detected services.
        """
        vuln_dict = {}

        # שלב 1: הפק שמות שירותים
        state = self.blackboard_api.get_state_for_agent(self.name)
        services = state.get("target", {}).get("services", [])
        service_names = {
            s.get("service", "").strip().lower()
            for s in services
            if s.get("service")
        }

        for s in sorted(service_names):
            print(f"  - {s}")

        # שלב 2: הרחבת שירותים לפי משפחות
        expanded_service_names = set()
        for service in service_names:
            family = SERVICE_FAMILIES.get(service, [service])
            expanded = [name.lower() for name in family]
            expanded_service_names.update(expanded)


        # שלב 3: חיפוש התאמות בין CVE→CPE למוצרים
        print(f"[LOG] Checking {len(self.cve_items)} CVEs for product name matches...")
        self.cve_items = load_cve_database(DATASET_NVD_CVE_CPE_PATH)
        for item in self.cve_items:
            try:
                cve_id = item["cve"]
                cpes = item.get("cpes", [])
                matched = []

                for cpe_uri in cpes:
                    parts = cpe_uri.split(":")
                    if len(parts) < 5:
                        print("hi")
                        continue
                    product = parts[4].strip().lower()

                    if product in expanded_service_names:
                        matched.append(cpe_uri)

                if matched:
                    vuln_dict[cve_id] = {
                        "cve": cve_id,
                        "matched_cpes": matched,
                        "cvss": 0.0  # ניתן לעדכן בהמשך
                    }
                    #print(f"[✓] CVE {cve_id} matched {len(matched)} CPEs")

            except Exception as e:
                print(f"[!] Failed parsing CVE record: {e}")
                continue

        #print(f"[LOG] Total CVEs matched by product name: {len(vuln_dict)}")

        # שלב 4: סינון לפי מאגר Metasploit
        metasploit_cves = {entry["cve"] for entry in self.metasploit_dataset if "cve" in entry}
        #print(f"[LOG] Total CVEs in Metasploit dataset: {len(metasploit_cves)}")

        filtered = []
        for v in vuln_dict.values():
            if v["cve"] in metasploit_cves:
                filtered.append(v)
                #print(f"[FINAL] CVE {v['cve']} passed Metasploit filter ✅")

        print(f"[LOG] Final matched CVEs after Metasploit filter: {len(filtered)}")
        return filtered


    def generate_possible_cpes(self, state_dict):
        target = state_dict.get("target", {})
        cpes = set()
        known_services = set()

        # === OS to CPE ===
        os_info = target.get("os", {})
        distro = os_info.get("distribution", {})
        if distro.get("name"):
            name = distro["name"].strip().lower().replace(" ", "_")
            cpes.add(f"cpe:2.3:o:{name}:{name}:*:*:*:*:*:*:*:*")
            if distro.get("version"):
                ver = distro["version"].strip().lower().replace(" ", "_")
                cpes.add(f"cpe:2.3:o:{name}:{name}:{ver}:*:*:*:*:*:*:*:*")

        # === Services to CPE ===
        for s in target.get("services", []):
            name = s.get("service", "").strip().lower().replace(" ", "_")
            version = s.get("server_version", "").strip().lower()
            if not name:
                continue
            known_services.add(name)

            for cpe in self._generate_service_cpes(name, name):
                cpes.add(cpe)

            if version:
                cpes.add(f"cpe:2.3:a:{name}:{name}:{version}:*:*:*:*:*:*:*:*")

        # === Web Directories Heuristics ===
        dirs = state_dict.get("web_directories_status", {})
        for code in ("200", "403"):
            for path in dirs.get(code, {}):
                dir_name = path.strip("/").lower()
                if dir_name and "/" not in dir_name:
                    for cpe in self._generate_service_cpes(dir_name, dir_name):
                        cpes.add(cpe)

        print(f"[VulnAgent] Generated {len(cpes)} CPEs (initial + level-1 expansion).")
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

def load_cve_database(path):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data.append(orjson.loads(line))
                    except Exception as e:
                        print(f"[!] Failed to parse line: {e}")
        return data

if __name__ == "__main__":

    print("[*] Loading CVE→CPE pre-parsed dataset...")
    cve_items = load_cve_database(DATASET_NVD_CVE_CPE_PATH)
    print(f"[+] Loaded {len(cve_items)} CVE→CPE entries")

    # מצב בדיקה ידני
    #test_state = {'target': {'geo_location': {'city': 'Tel Aviv', 'country': '', 'region': ''}, 'hostname': 'METASPLOITABLE', 'ip': '192.168.56.101', 'netbios_name': 'WIN-101PC56', 'os': {'distribution': {'architecture': 'x86', 'name': 'ubuntu', 'version': '7.95'}, 'kernel': '', 'name': 'linux'}, 'rpc_services': [{'program_number': '111', 'version': '', 'protocol': 'tcp', 'port': '111', 'service_name': 'rpcbind'}], 'services': [{'port': '21', 'protocol': 'tcp', 'service': 'ftp', 'server_type': '', 'server_version': ''}, {'port': '21', 'protocol': 'tcp', 'service': 'ftp', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '22', 'protocol': 'tcp', 'service': 'ssh', 'server_type': '', 'server_version': ''}, {'port': '22', 'protocol': 'tcp', 'service': 'ssh', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '23', 'protocol': 'tcp', 'service': 'telnet', 'server_type': '', 'server_version': ''}, {'port': '23', 'protocol': 'tcp', 'service': 'telnet', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '25', 'protocol': 'tcp', 'service': 'smtp', 'server_type': '', 'server_version': ''}, {'port': '25', 'protocol': 'tcp', 'service': 'smtp', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '53', 'protocol': 'tcp', 'service': 'domain', 'server_type': '', 'server_version': ''}, {'port': '53', 'protocol': 'tcp', 'service': 'domain', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '80', 'protocol': 'tcp', 'service': 'http', 'server_type': '', 'server_version': ''}, {'port': '80', 'protocol': 'tcp', 'service': 'http', 'server_type': 'Apache', 'server_version': '2.2.8 (Ubuntu)'}, {'port': '80', 'protocol': 'tcp', 'service': 'http', 'server_type': 'Apache', 'server_version': 'Apache/2.2.8 (Ubuntu)'}, {'port': '80', 'protocol': 'tcp', 'service': 'http', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '111', 'protocol': 'tcp', 'service': 'rpcbind', 'server_type': '', 'server_version': ''}, {'port': '111', 'protocol': 'tcp', 'service': 'rpcbind', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '139', 'protocol': 'tcp', 'service': 'netbios-ssn', 'server_type': '', 'server_version': ''}, {'port': '139', 'protocol': 'tcp', 'service': 'netbios-ssn', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '445', 'protocol': 'tcp', 'service': 'microsoft-ds', 'server_type': '', 'server_version': ''}, {'port': '445', 'protocol': 'tcp', 'service': 'microsoft-ds', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '512', 'protocol': 'tcp', 'service': 'exec', 'server_type': '', 'server_version': ''}, {'port': '513', 'protocol': 'tcp', 'service': 'login', 'server_type': '', 'server_version': ''}, {'port': '513', 'protocol': 'tcp', 'service': 'login', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '514', 'protocol': 'tcp', 'service': 'shell', 'server_type': '', 'server_version': ''}, {'port': '514', 'protocol': 'tcp', 'service': 'shell', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '1099', 'protocol': 'tcp', 'service': 'rmiregistry', 'server_type': '', 'server_version': ''}, {'port': '1524', 'protocol': 'tcp', 'service': 'ingreslock', 'server_type': '', 'server_version': ''}, {'port': '2049', 'protocol': 'tcp', 'service': 'nfs', 'server_type': '', 'server_version': ''}, {'port': '2049', 'protocol': 'tcp', 'service': 'nfs', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '2121', 'protocol': 'tcp', 'service': 'ccproxy-ftp', 'server_type': '', 'server_version': ''}, {'port': '2121', 'protocol': 'tcp', 'service': 'ccproxy-ftp', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '3306', 'protocol': 'tcp', 'service': '', 'server_type': '', 'server_version': ''}, {'port': '3306', 'protocol': 'tcp', 'service': 'mysql', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '5432', 'protocol': 'tcp', 'service': '', 'server_type': '', 'server_version': ''}, {'port': '5432', 'protocol': 'tcp', 'service': 'postgresql', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '5900', 'protocol': 'tcp', 'service': '', 'server_type': '', 'server_version': ''}, {'port': '5900', 'protocol': 'tcp', 'service': 'vnc', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '6000', 'protocol': 'tcp', 'service': 'X11', 'server_type': '', 'server_version': ''}, {'port': '6000', 'protocol': 'tcp', 'service': 'X11', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '6667', 'protocol': 'tcp', 'service': 'irc', 'server_type': '', 'server_version': ''}, {'port': '8009', 'protocol': 'tcp', 'service': 'ajp13', 'server_type': '', 'server_version': ''}, {'port': '8009', 'protocol': 'tcp', 'service': 'ajp13', 'server_type': 'NO', 'server_version': 'NO'}, {'port': '8180', 'protocol': 'tcp', 'service': 'unknown', 'server_type': '', 'server_version': ''}, {'port': '', 'protocol': '', 'service': '', 'server_type': '', 'server_version': 'NO'}], 'ssl': {'issuer': '', 'protocols': []}}, 'actions_history': ['nmap -F 192.168.56.101', 'nmap 192.168.56.101', 'httpx http://192.168.56.101', 'nbtscan 192.168.56.101', 'nbtscan 192.168.56.101', 'nbtscan 192.168.56.101'], 'cpes': [], 'vulnerabilities_found': [], 'attack_impact': {}, 'failed_CVEs': []}

    test_state = {
  "target": {
    "hostname": "",
    "netbios_name": "",
    "os": {
      "name": "Linux",
      "distribution": {
        "name": "Ubuntu",
        "version": "8.04",
        "architecture": "x86"
      },
      "kernel": "2.6.24"
    },
    "services": [
      {
        "port": "",
        "protocol": "",
        "service": "",
        "server_type": "",
        "server_version": ""
      },
      {
        "port": "21",
        "protocol": "tcp",
        "service": "ftp",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "22",
        "protocol": "tcp",
        "service": "ssh",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "23",
        "protocol": "tcp",
        "service": "telnet",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "25",
        "protocol": "tcp",
        "service": "smtp",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "53",
        "protocol": "tcp",
        "service": "domain",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "80",
        "protocol": "tcp",
        "service": "http",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "111",
        "protocol": "tcp",
        "service": "rpcbind",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "139",
        "protocol": "tcp",
        "service": "netbios-ssn",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "445",
        "protocol": "tcp",
        "service": "microsoft-ds",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "513",
        "protocol": "tcp",
        "service": "login",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "514",
        "protocol": "tcp",
        "service": "shell",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "2049",
        "protocol": "tcp",
        "service": "nfs",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "2121",
        "protocol": "tcp",
        "service": "ccproxy-ftp",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "3306",
        "protocol": "tcp",
        "service": "mysql",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "5432",
        "protocol": "tcp",
        "service": "postgresql",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "5900",
        "protocol": "tcp",
        "service": "vnc",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "6000",
        "protocol": "tcp",
        "service": "X11",
        "server_type": "NO",
        "server_version": "NO"
      },
      {
        "port": "8009",
        "protocol": "tcp",
        "service": "ajp13",
        "server_type": "NO",
        "server_version": "NO"
      }
    ],
    "rpc_services": [
      {
        "program_number": "",
        "version": "",
        "protocol": "",
        "port": "",
        "service_name": ""
      },
      {
        "program_number": "111",
        "version": "",
        "protocol": "tcp",
        "port": "111",
        "service_name": "rpcbind"
      }
    ],
    "geo_location": {
      "country": "",
      "region": "",
      "city": "Tel Aviv"
    },
    "ssl": {
      "issuer": "",
      "protocols": [
        ""
      ]
    },
    "ip": "192.168.56.101"
  },
  "actions_history": [
    "nmap -F 192.168.56.101",
    "nmap -F 192.168.56.101",
    "nmap -F 192.168.56.101",
    "nmap -F 192.168.56.101",
    "nmap -F 192.168.56.101",
    "nmap -F 192.168.56.101",
    "nmap -F 192.168.56.101"
  ],
  "cpes": [
    "cpe:2.3:a:*:x11:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:http:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:http:http:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ccproxy-ftp:ccproxy-ftp:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:postgresql:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:domain:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:shell:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:http:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ccproxy-ftp:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:rpcbind:rpcbind:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:rpcbind:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:netbios-ssn:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:telnet:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:telnet:telnet:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:postgresql:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:login:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:http:http:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:postgresql:postgresql:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:x11:x11:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:mysql:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ajp13:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:ccproxy-ftp:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:telnet:telnet:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:domain:domain:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:netbios-ssn:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:login:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:shell:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:nfs:nfs:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:vnc:vnc:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:ssh:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:shell:shell:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ccproxy-ftp:ccproxy-ftp:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ssh:ssh:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:mysql:mysql:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ssh:ssh:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:smtp:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:login:login:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:vnc:vnc:*:*:*:*:*:*:*:*",
    "cpe:2.3:o:ubuntu:ubuntu:8.04:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:microsoft-ds:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:mysql:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:netbios-ssn:netbios-ssn:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:vnc:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:ajp13:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:microsoft-ds:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:x11:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ajp13:ajp13:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ftp:ftp:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:nfs:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:x11:x11:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:telnet:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:domain:domain:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:microsoft-ds:microsoft-ds:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:rpcbind:rpcbind:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ftp:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ssh:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:smtp:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:rpcbind:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:microsoft-ds:microsoft-ds:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:shell:shell:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:*:ftp:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:login:login:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ajp13:ajp13:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:domain:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:postgresql:postgresql:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:mysql:mysql:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:vnc:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:nfs:*:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:ftp:ftp:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:nfs:nfs:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:o:ubuntu:ubuntu:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:smtp:smtp:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:smtp:smtp:no:*:*:*:*:*:*:*:*",
    "cpe:2.3:a:netbios-ssn:netbios-ssn:*:*:*:*:*:*:*:*"
  ],
  "vulnerabilities_found": [],
  "attack_impact": {},
  "failed_CVEs": []
}

    class DummyBlackboardAPI:
        def get_state_for_agent(self, name):
            return test_state

        @property
        def blackboard(self):
            return {}

    # צור את הסוכן והפעל את הפונקציות
    agent = VulnAgent(
        blackboard_api=DummyBlackboardAPI(),
        cve_items=cve_items,
        epsilon=0.0,
        os_linux_dataset=None,
        os_linux_kernel_dataset=None,
        metasploit_dataset=[{"cve": m["cve"]} for m in cve_items]  # לבדיקה נניח שכולם במטאספלויט
    )

    possible_cpes = agent.generate_possible_cpes(test_state)
    matches = agent.match_cves_to_cpes(possible_cpes)
    matches = agent.filter_top_vulnerabilities(matches, top_n=900)

    print(f"\n[✓] Found top {len(matches)} CVEs matching the generated CPEs:\n")
    for match in matches:
        cve_id = match['cve']
        cvss = match.get("cvss", "N/A")
        print(f"  - CVE: {cve_id}  (CVSS: {cvss})")
        for cpe in match['matched_cpes']:
            print(f"      • {cpe}")
        print()
