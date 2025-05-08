import sys
import os
import requests
from tqdm import tqdm
import gzip
import shutil

from config import TEMPORARY_NVD_CVE_PATH

download_dir = os.path.expanduser(TEMPORARY_NVD_CVE_PATH)
os.makedirs(download_dir, exist_ok=True)

years = list(range(2002, 2025))
base_url = "https://nvd.nist.gov/feeds/json/cve/1.1"

def download_file(url, dest_path, json_dest_path):

    if os.path.exists(json_dest_path):
        print(f"✅ File {os.path.basename(json_dest_path)} is exist, skiping...")
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
            print(f"✅ File {json_path} exists, skiping...")

print("✅ NVD dataset Downloaded successfully.")
