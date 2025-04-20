import os
import sys
import json
import gzip
import shutil
import requests
from tqdm import tqdm
from pathlib import Path

# שלב 1: הורדת קבצי CVE בפורמט .gz לכל שנה
def download_file(url, dest_path, json_dest_path):
    if os.path.exists(json_dest_path):
        print(f"✅ File {os.path.basename(json_dest_path)} already exists, skipping...")
        return

    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length', 0))
    with open(dest_path, 'wb') as file, tqdm(
        desc=os.path.basename(dest_path),
        total=total,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            file.write(data)
            bar.update(len(data))

def download_nvd_dataset(download_dir):
    print("⬇️ Downloading NVD dataset...")
    years = list(range(2002, 2025))
    base_url = "https://nvd.nist.gov/feeds/json/cve/1.1"

    for year in years:
        filename = f"nvdcve-1.1-{year}.json.gz"
        url = f"{base_url}/{filename}"
        dest_path = os.path.join(download_dir, filename)
        json_path = os.path.join(download_dir, f"nvdcve-1.1-{year}.json")
        download_file(url, dest_path, json_path)

    for file in os.listdir(download_dir):
        if file.endswith(".gz"):
            gz_path = os.path.join(download_dir, file)
            json_path = gz_path[:-3]
            if not os.path.exists(json_path):
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(json_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(gz_path)
            else:
                print(f"✅ File {json_path} already extracted, skipping...")

    print("✅ NVD dataset downloaded and extracted successfully.")

# שלב 2: שילוב כל קבצי ה-CVE לקובץ אחד
def combine_nvd_files(download_dir, CVE_PATH):
    if os.path.exists(CVE_PATH):
        print(f"✅ Combined CVE file already exists, skipping...")
        return

    print("⬇️ Combining CVE JSON files...")
    all_cves = []
    for filename in sorted(os.listdir(download_dir)):
        if filename.endswith(".json"):
            file_path = os.path.join(download_dir, filename)
            if not os.path.exists(file_path):
                print(f"❌ File {filename} does not exist, skipping...")
                continue
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    all_cves.extend(data.get("CVE_Items", []))
                except json.JSONDecodeError:
                    print(f"❌ JSON decode error in file: {filename}")

    with open(CVE_PATH, "w") as f:
        json.dump(all_cves, f, indent=2)

    print(f"✅ Combined CVE dataset saved : total {len(all_cves)} CVEs\n")

# פונקציה ראשית מאוחדת
def download_nvd_cve(NVD_CVE_PATH, CVE_PATH):
    download_dir = os.path.expanduser(NVD_CVE_PATH)
    os.makedirs(download_dir, exist_ok=True)

    download_nvd_dataset(download_dir)
    combine_nvd_files(download_dir, CVE_PATH)