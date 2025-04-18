import os
import subprocess

# הגדרת הנתיב לתיקיית ההורדה
NVD_DOWNLOAD_SCRIPT = "create_cve_dataset/download_cve.py"  # שם הקובץ הראשון
COMBINE_CVE_SCRIPT = "create_cve_dataset/combine_cve_files.py"    # שם הקובץ השני

def run_file(script_name):
    """פונקציה להרצת סקריפט פייתון"""
    try:
        subprocess.check_call(["python", script_name])
    except subprocess.CalledProcessError as e:
        print(f"❌ שגיאה בהרצת הסקריפט {script_name}: {e}")

def download_nvd_cve(script_name):
    run_file(NVD_DOWNLOAD_SCRIPT)  # הרצת הסקריפט הראשון
    run_file(COMBINE_CVE_SCRIPT)   # הרצת הסקריפט השני
