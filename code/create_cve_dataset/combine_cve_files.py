import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import NVD_CVE_PATH, CVE_PATH

all_cves = []

target_dir = NVD_CVE_PATH

# בדיקה אם הקובץ קיים ב־CVE_PATH
if os.path.exists(CVE_PATH):
    print(f"✅ File nvd_cve_dataset.json exists, skiping...")
    exit() 

# מעבר על כל הקבצים בתיקייה הנוכחית
for filename in sorted(os.listdir(target_dir)):
    if filename.endswith(".json"):
        file_path = os.path.join(target_dir, filename)
        
        # בדיקה אם הקובץ כבר קיים לפני קריאתו
        if not os.path.exists(file_path):
            print(f"❌ הקובץ {filename} לא קיים בתיקייה {target_dir}.")
            continue  # אם הקובץ לא קיים, נדלג עליו

        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
                all_cves.extend(data.get("CVE_Items", []))
            except json.JSONDecodeError:
                print(f"שגיאה בקריאת הקובץ: {filename}")

# שמירה לקובץ JSON חדש
output_file = os.path.join(target_dir, "nvd_cve_dataset.json")
with open(output_file, "w") as f:
    json.dump(all_cves, f, indent=2)

print(f"✅ NVD dataset Combined successfully: Total {len(all_cves)} CVEs")
