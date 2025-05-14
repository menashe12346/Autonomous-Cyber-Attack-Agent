import subprocess

PROJECT_PATH = "/mnt/linux-data/project"

# LLM Model configuration
LLAMA_RUN_PATH = f"{PROJECT_PATH}/code/models/llama.cpp/build/bin/llama-run"
MISTRAL_MODEL_PATH = f"{PROJECT_PATH}/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf"

def run(prompt: str, context_num = 1) -> str:
    response = ""
    context_length = str(context_num * 50)

    cmd = [
        LLAMA_RUN_PATH,
        "--context-size", context_length,
        MISTRAL_MODEL_PATH,
        prompt
    ]


    try:
        output = subprocess.check_output(cmd, text=True).strip()
        response += output
    except subprocess.CalledProcessError:
        pass
    return response

command_output = "hi"

response = run(command_output)
print(f"1: {response}")
response = run(command_output)
print(f"1: {response}")
response = run(command_output)
print(f"1: {response}")
response = run(command_output)
print(f"1: {response}")
response = run(command_output)
print(f"1: {response}")
response = run(command_output)
print(f"1: {response}")

response = run(command_output)
print(f"1: {response}")



