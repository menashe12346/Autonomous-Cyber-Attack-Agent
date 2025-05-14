import subprocess
import tempfile
import time
import os

PROJECT_PATH = "/mnt/linux-data/project"
LLAMA_RUN_PATH = f"{PROJECT_PATH}/code/models/llama.cpp/build/bin/llama-run"
MODEL_PATH = f"{PROJECT_PATH}/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"

def run_llama_via_script(prompt):
    with tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".log") as log_file:
        log_path = log_file.name

    # בנה את הפקודה שנריץ דרך script
    command = (
        f"script -q -c \"echo '{prompt}' | {LLAMA_RUN_PATH} "
        f"--context-size 4096 {MODEL_PATH}\" {log_path}"
    )

    subprocess.run(command, shell=True)

    # המתן שהקובץ יתעדכן
    time.sleep(1)

    # קרא את הפלט מתוך הלוג
    with open(log_path, "r") as f:
        lines = f.readlines()

    os.remove(log_path)

    # מצא את השורה של המענה האמיתי (תלוי ב־llama-run)
    # נסנן שורות של קלט, פקודות וכו׳
    response_lines = [line.strip() for line in lines if prompt not in line and line.strip()]
    return "\n".join(response_lines)

# דוגמה:
print("Response 1:")
print(run_llama_via_script("hi"))

print("\nResponse 2:")
print(run_llama_via_script("what is the capital of Italy?"))
