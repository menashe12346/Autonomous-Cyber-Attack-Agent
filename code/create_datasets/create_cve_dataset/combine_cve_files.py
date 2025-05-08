import sys
import os
import json

from config import TEMPORARY_NVD_CVE_PATH, DATASET_NVD_CVE_PATH

all_cves = []

target_dir = TEMPORARY_NVD_CVE_PATH

if os.path.exists(DATASET_NVD_CVE_PATH):
    print(f"✅ File nvd_cve_dataset.json exists, skiping...")
    exit() 

for filename in sorted(os.listdir(target_dir)):
    if filename.endswith(".json"):
        file_path = os.path.join(target_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"❌ The file {filename} doesn't exist in the folder {target_dir}.")
            continue 

        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
                all_cves.extend(data.get("CVE_Items", []))
            except json.JSONDecodeError:
                print(f"Error reading the file: {filename}")

output_file = os.path.join(target_dir, "nvd_cve_dataset.json")
with open(output_file, "w") as f:
    json.dump(all_cves, f, indent=2)

print(f"✅ NVD dataset Combined successfully: Total {len(all_cves)} CVEs")
