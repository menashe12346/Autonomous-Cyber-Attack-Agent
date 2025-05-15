import subprocess
import tempfile
import time
import os
import tiktoken

from models.llm.base_llm import BaseLLM
from config import LLAMA_RUN_PATH, MISTRAL_MODEL_PATH

class LlamaModel(BaseLLM):
    """
    LLM interface for executing prompts using llama.cpp binary.
    Supports single or multiple prompts with contextual memory.
    """

    def __init__(self, context_size=3000):
        self.context_size= context_size
        
        print("✅ Llama Model initialized successfully.")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string using cl100k_base tokenizer.
        """
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))

    def run(self, prompt: str, context_num = 1) -> str:
        context_length = str(context_num * self.context_size)

        # כתיבת ה-prompt לקובץ זמני
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as prompt_file:
            prompt_file.write(prompt)
            prompt_path = prompt_file.name

        with tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".log") as log_file:
            log_path = log_file.name

        # בנה את הפקודה לשימוש דרך קובץ (ולא echo)
        command = (
            f"script -q -c \"{LLAMA_RUN_PATH} --context-size {context_length} {MISTRAL_MODEL_PATH} < {prompt_path}\" {log_path}"
        )

        print(f"[LLAMA] Number of Tokens     ({self.count_tokens(prompt)}): {repr(prompt)}")

        try:
            subprocess.run(command, shell=True)
        except:
            pass

        # המתן שהקובץ יתעדכן
        time.sleep(1)

        # קריאת פלט
        with open(log_path, "r") as f:
            lines = f.readlines()

        # ניקוי קבצים זמניים
        os.remove(prompt_path)
        os.remove(log_path)

        # החזרת שורות מתאימות
        response_lines = [line.strip() for line in lines if prompt not in line and line.strip()]
        return "\n".join(response_lines)
