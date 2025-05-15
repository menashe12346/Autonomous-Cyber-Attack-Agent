import orjson
import os
from pathlib import Path

from config import DATASET_NVD_CVE_PATH, DATASET_NVD_CVE_CPE_PATH

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

def create_cve_cpe_dataset():
    # בדוק אם כבר נבנה
    if os.path.exists(DATASET_NVD_CVE_CPE_PATH):
        print(f"[✓] Index file already exists: {DATASET_NVD_CVE_CPE_PATH} — Skipping.")
        return

    print(f"[+] Loading CVE data from: {DATASET_NVD_CVE_PATH}")
    with open(DATASET_NVD_CVE_PATH, "rb") as f:
        data = orjson.loads(f.read())

    cve_items = data
    print(f"[✓] Loaded {len(cve_items)} CVE entries.")

    count_written = 0

    with open(DATASET_NVD_CVE_CPE_PATH, "w", encoding="utf-8") as out_f:
        for item in cve_items:
            try:
                cve_id = item["cve"]["CVE_data_meta"]["ID"]
                nodes = item.get("configurations", {}).get("nodes", [])
                all_cpes = set()

                for node in nodes:
                    for match in extract_all_cpe_matches(node):
                        uri = match.get("cpe23Uri", "").strip().lower()
                        if uri:
                            all_cpes.add(uri)

                if all_cpes:
                    record = {
                        "cve": cve_id,
                        "cpes": sorted(all_cpes)
                    }
                    out_f.write(orjson.dumps(record).decode("utf-8") + "\n")
                    count_written += 1

            except Exception as e:
                print(f"[!] Failed parsing CVE: {e}")
                continue

    print(f"[✓] Finished. Wrote {count_written} CVE→CPE mappings to: {DATASET_NVD_CVE_CPE_PATH}")