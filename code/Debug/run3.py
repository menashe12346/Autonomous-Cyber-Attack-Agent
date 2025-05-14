import subprocess
import time
import os

PROJECT_PATH = "/mnt/linux-data/project"
LLAMA_RUN_PATH = f"{PROJECT_PATH}/code/models/llama.cpp/build/bin/llama-run"
MODEL_PATH = f"{PROJECT_PATH}/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"
SESSION_FILE = "/tmp/llama_session.txt"

# פקודת shell שמריצה את llama-run תחת script ושומרת את כל הפלט
cmd = f'script -q -c "{LLAMA_RUN_PATH} --context-size 4096 {MODEL_PATH}" {SESSION_FILE}'

# מפעילים את התהליך
proc = subprocess.Popen(
    cmd,
    shell=True,
    stdin=subprocess.PIPE,
    text=True
)

# זמן טעינה ראשונית
time.sleep(10)

# שולחים פקודת שיחה
proc.stdin.write("Hi there!\n")
proc.stdin.flush()
time.sleep(5)

proc.stdin.write("What is the capital of France?\n")
proc.stdin.flush()
time.sleep(5)

# סיום
proc.stdin.write("exit\n")
proc.stdin.flush()
time.sleep(2)
proc.terminate()

# קריאה מהקובץ
print("\n========== RESPONSE ==========")
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
        data = f.read()
        print(data)
else:
    print("❌ Failed to read output.")
