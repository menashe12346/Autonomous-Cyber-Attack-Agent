import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import re

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import OS_LINUX_DATASET, OS_LINUX_KERNEL_DATASET, TEMPORARY_DISTROWATCH_FILES

# כתובות
BASE_URL = "https://distrowatch.com"
DISTRO_PAGE_BASE = f"{BASE_URL}/table.php?distribution="

# קבצים ותיקיות
DATA_DIR = Path(TEMPORARY_DISTROWATCH_FILES)
DISTRO_DIR = DATA_DIR / "distros"
POP_PAGE = DATA_DIR / "popularity.html"
FINAL_DATASET_PATH = DATA_DIR / "os_dataset.json"

# הגדרות
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

# הכנה
DATA_DIR.mkdir(parents=True, exist_ok=True)
DISTRO_DIR.mkdir(parents=True, exist_ok=True)
def extract_distro_names():
    """
    מחלץ את שם ההפצה המלא ואת ה-slug (href) מהחלק של Last 12 months.
    """
    print("[*] Extracting distribution names from Last 12 months section...")
    soup = BeautifulSoup(POP_PAGE.read_text(encoding="utf-8"), "html.parser")

    last_12_months_table = None
    for table in soup.find_all("table"):
        th = table.find("th", class_="Invert")
        if th and "Last 12 months" in th.text:
            last_12_months_table = table
            break

    if last_12_months_table is None:
        print("[!] Could not find 'Last 12 months' section.")
        return []

    distros = []
    for row in last_12_months_table.find_all("tr"):
        phr2_td = row.find("td", class_="phr2")
        if phr2_td:
            link = phr2_td.find("a", href=True)
            if link:
                name = link.text.strip()
                slug = link["href"].strip().lower()
                if name and slug:
                    distros.append({"name": name, "slug": slug})

    # הסרת כפילויות לפי name
    seen = set()
    unique_distros = []
    for d in distros:
        if d["name"].lower() not in seen:
            seen.add(d["name"].lower())
            unique_distros.append(d)

    print(f"[+] Found {len(unique_distros)} unique distributions.")
    return unique_distros


def download_distro_pages(distros):
    """
    מוריד רק את דפי ההפצות (table.php) לפי שם ההפצה המלא, אם עדיין לא קיימים מקומית.
    """
    print("[*] Checking for missing distribution pages...")

    existing_files = {p.stem.lower() for p in DISTRO_DIR.glob("*.html")}
    missing = [d for d in distros if d["name"].lower() not in existing_files]

    print(f"[+] {len(missing)} missing distribution pages to download.")

    for idx, distro in enumerate(missing, start=1):
        name = distro["name"]
        slug = distro["slug"]
        output_file = DISTRO_DIR / f"{name}.html"
        url = f"{DISTRO_PAGE_BASE}{slug}"

        try:
            print(f"[{idx}/{len(missing)}] Downloading table page for {name}...")
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                output_file.write_text(resp.text, encoding="utf-8")
            else:
                print(f"[!] Failed table page for {name}, status {resp.status_code}")
        except Exception as e:
            print(f"[!] Error downloading table page for {name}: {e}")

        time.sleep(2)

    if not missing:
        print("[✓] No missing distribution pages to download.")


def download_distro_indexes(distros):
    """
    מוריד גם את index.php?distribution=SLUG לכל הפצה,
    ושומר בקובץ בשם המלא של ההפצה בתוך תיקיית distro_indexes.
    """
    print("[*] Downloading distro index pages...")

    distro_index_dir = DATA_DIR / "distro_indexes"
    distro_index_dir.mkdir(parents=True, exist_ok=True)

    existing_files = {p.stem.lower() for p in distro_index_dir.glob("*.html")}
    missing = [d for d in distros if d["name"].lower() not in existing_files]

    print(f"[+] {len(missing)} missing index pages to download.")

    for idx, distro in enumerate(missing, start=1):
        name = distro["name"]
        slug = distro["slug"]
        output_file = distro_index_dir / f"{name}.html"
        url = f"{BASE_URL}/index.php?distribution={slug}"

        try:
            print(f"[{idx}/{len(missing)}] Downloading index page for {name}...")
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                output_file.write_text(resp.text, encoding="utf-8")
            else:
                print(f"[!] Failed index page for {name}, status {resp.status_code}")
        except Exception as e:
            print(f"[!] Error downloading index page for {name}: {e}")

        time.sleep(2)

    if not missing:
        print("[✓] No missing index pages to download.")

def update_versions_in_dataset():
    """
    מעדכן גרסאות של כל הפצה לפי קבצי index,
    ושומר בתוך os_dataset.json ע"י הוספת שדה versions.
    """
    distro_index_dir = DATA_DIR / "distro_indexes"
    dataset_path = Path(OS_LINUX_DATASET)

    if not dataset_path.exists():
        print("[!] Dataset file not found.")
        return

    # טען את הקובץ כ- dict (ולא list!)
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # עבור כל קובץ index
    for index_file in distro_index_dir.glob("*.html"):
        distro_name = index_file.stem.strip()
        print(f"[*] Processing: {distro_name}")

        if distro_name.lower() not in dataset:
            print(f"[!] {distro_name} not found in dataset.")
            continue

        soup = BeautifulSoup(index_file.read_text(encoding="utf-8"), "html.parser")
        versions_found = []

        for td in soup.find_all("td", class_="NewsHeadline"):
            text = td.get_text(separator=" ", strip=True)

            if "Distribution Release" in text or "Development Release" in text:
                a_tag = td.find("a", href=True)
                if not a_tag:
                    continue

                a_text = a_tag.get_text(strip=True)

                if "3CX Phone System" in a_text:
                    continue  # התעלמות מיוחדת

                # חיפוש גרסה (לוקח את המספר הראשון בלבד)
                match = re.search(r"\d+(\.\d+)*", a_text)
                if match:
                    version = match.group()
                    versions_found.append(version)

        if versions_found:
            print(f"[+] {distro_name} → {len(versions_found)} versions: {versions_found}")
            dataset[distro_name.lower()]["versions"] = versions_found
        else:
            print(f"[-] {distro_name}: No versions found.")

    # שמירה חזרה לקובץ
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print("[✔] All versions updated and saved.")


BASE_URL = "https://cdn.kernel.org/pub/linux/kernel/"

def fetch_kernel_versions():
    response = requests.get(BASE_URL)
    if response.status_code != 200:
        print("Failed to fetch base page.")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('v')]

    versions = []

    for link in links:
        folder_url = BASE_URL + link
        sub_response = requests.get(folder_url)
        if sub_response.status_code != 200:
            continue

        sub_soup = BeautifulSoup(sub_response.text, "html.parser")
        for a in sub_soup.find_all('a', href=True):
            href = a['href']
            if href.endswith(".tar.gz") or href.endswith(".tar.xz"):
                # דוגמה: linux-6.8.2.tar.xz
                if href.startswith("linux-") and "patch" not in href:
                    version = href.split("linux-")[1].split(".tar")[0]
                    versions.append(version)
    
    versions = sorted(set(versions))
    
    with open(OS_LINUX_KERNEL_DATASET, "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(versions)} kernel versions to {OS_LINUX_KERNEL_DATASET}")

def build_architecture_dataset():
    """
    בונה קובץ JSON שבו לכל הפצה יש מפתח 'architecture' שמכיל את רשימת הארכיטקטורות שלה.
    """
    print("[*] Building architecture dataset...")
    architecture_dataset = {}
    distro_files = list(DISTRO_DIR.glob("*.html"))

    print(f"[*] Found {len(distro_files)} distro files to process.\n")

    for idx, path in enumerate(distro_files, start=1):
        distro_name = path.stem.lower()  # שם ההפצה מהקובץ
        architectures = extract_architectures_from_html(path)

        if architectures:
            architecture_dataset[distro_name] = {"architecture": architectures}
            print(f"[{idx}/{len(distro_files)}] {distro_name}: {architectures}")
        else:
            print(f"[{idx}/{len(distro_files)}] {distro_name}: No architectures found.")

    Path(OS_LINUX_DATASET).write_text(json.dumps(architecture_dataset, indent=2), encoding="utf-8")

    update_versions_in_dataset()

    print(f"\n[✔] Architecture dataset complete.")
    print(f"[✔] Saved to: {OS_LINUX_DATASET}")
    print(f"[✔] Total distributions processed: {len(architecture_dataset)}")

def extract_architectures_from_html(path):
    """
    מחלץ ארכיטקטורות ע"י ניתוח ישיר של HTML גולמי:
    מחפש את <b>Architecture:</b> ואז סורק את הטקסט הגולמי עד סוף רשימת הארכיטקטורות לפי פסיקים.
    """
    html = path.read_text(encoding="utf-8")

    # מצא את התחלת הקטע שמכיל Architecture
    start_index = html.lower().find("<b>architecture:</b>")
    if start_index == -1:
        return []

    # קח את החלק אחרי Architecture
    sub_html = html[start_index:]

    # חתוך עד ל-<li> הבא או סוף שורה
    end_index = sub_html.lower().find("<li>")
    if end_index != -1:
        sub_html = sub_html[:end_index]

    # מצא את כל הארכיטקטורות לפי תבנית a-tag
    soup = BeautifulSoup(sub_html, "html.parser")
    architectures = []

    for a in soup.find_all("a", href=True):
        text = a.text.strip()
        if text:
            architectures.append(text)

    return architectures

def download_os_linux_dataset():
    if not Path(OS_LINUX_DATASET).exists():
        distro_names = extract_distro_names()
        download_distro_pages(distro_names)
        download_distro_indexes(distro_names)
        build_architecture_dataset()

    if not Path(OS_LINUX_KERNEL_DATASET).exists():
        fetch_kernel_versions()

if __name__ == "__main__":
    download_os_linux_dataset()
