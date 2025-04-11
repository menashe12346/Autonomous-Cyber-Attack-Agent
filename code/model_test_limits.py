import subprocess
import os

LLAMA_RUN = "/mnt/linux-data/project/code/models/llama.cpp/build/bin/llama-run"
MODEL_PATH = "file:///mnt/linux-data/project/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"
PROMPT = "Generate a very long list of numbers starting from 1.\n1."
THREADS = "4"
N_BATCH = "32"  # ערך שמרני ויציב

def is_available(path):
    return os.path.exists(path) and os.access(path, os.X_OK)

def test_token_limit():
    if not is_available(LLAMA_RUN):
        print(f"[!] Error: llama-run not found at {LLAMA_RUN}")
        return

    print(f"📍 Testing llama-run at: {LLAMA_RUN}")
    print(f"📍 Using model: {MODEL_PATH}\n")

    low = 1
    high = 8192
    best = 0

    print("🚀 Starting token limit test (with detailed errors)...")

    while low <= high:
        mid = (low + high) // 2
        print(f"🔍 Testing with {mid} tokens...", end=" ")

        cmd = [
            LLAMA_RUN,
            MODEL_PATH,
            PROMPT,
            "-n", str(mid),
            "-t", THREADS,
            "--n-batch", N_BATCH
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60*20)
            best = mid
            print("✅ Passed")
            low = mid + 1

        except subprocess.CalledProcessError as e:
            print("❌ Failed")
            print(f"    ↳ Return code: {e.returncode}")
            print(f"    ↳ stderr: {e.stderr.strip().splitlines()[-1] if e.stderr else 'No stderr'}")
            high = mid - 1

        except subprocess.TimeoutExpired:
            print("❌ Timeout")
            high = mid - 1

    print(f"\n🎯 Maximum usable tokens without crash: {best}")

if __name__ == "__main__":
    test_token_limit()
