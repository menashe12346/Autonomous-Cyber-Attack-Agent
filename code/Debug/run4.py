import subprocess
import tempfile
import os
import time

PROJECT_PATH = "/mnt/linux-data/project"
LLAMA_RUN_PATH = f"{PROJECT_PATH}/code/models/llama.cpp/build/bin/llama-run"
MODEL_PATH = f"{PROJECT_PATH}/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"

class PersistentLlamaScript:
    def __init__(self):
        self.log_file = tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".log")
        self.log_path = self.log_file.name
        self.log_file.close()

        self.pipe_in, self.pipe_out = tempfile.mkstemp()

        # הפעל את llama-run בתוך session של script עם pipe לקלט
        self.process = subprocess.Popen(
            f"script -q -c '{LLAMA_RUN_PATH} --context-size 4096 {MODEL_PATH}' {self.log_path}",
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            universal_newlines=True
        )

        print("Waiting for model to load...")
        time.sleep(10)  # זמן לטעינה – תוכל לכוונן לפי המהירות בפועל

    def send_prompt(self, prompt):
        if self.process.poll() is not None:
            raise RuntimeError("llama-run process has terminated.")

        with open(self.log_path, "r") as f:
            old_output = f.read()

        # שלח את הפרומפט
        self.process.stdin.write(prompt + "\n")
        self.process.stdin.flush()

        time.sleep(4)  # המתן שהמודל יגיב

        with open(self.log_path, "r") as f:
            new_output = f.read()

        # הבדל הפלטים – מה נוסף מאז
        diff = new_output[len(old_output):].strip()

        return diff

    def close(self):
        self.process.terminate()
        os.remove(self.log_path)
        os.close(self.pipe_in)
        os.remove(self.pipe_out)

# --- שימוש:
llama = PersistentLlamaScript()

print("Response 1:")
print(llama.send_prompt("Hi!"))

print("\nResponse 2:")
print(llama.send_prompt("What is the capital of Italy?"))

llama.close()
