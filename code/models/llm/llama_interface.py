import os
import subprocess
import tiktoken

from models.llm.base_llm import BaseLLM
from config import LLAMA_RUN_PATH, MISTRAL_MODEL_PATH

class LlamaModel(BaseLLM):
    """
    LLM interface for executing prompts using llama.cpp binary.
    Supports single or multiple prompts with contextual memory.
    """

    def __init__(self, context_size=9999):
        self.context_size= context_size
        
        print("✅ Llama Model initialized successfully.")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string using cl100k_base tokenizer.
        """
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))

    def run(self, prompt: str, context_num = 1) -> str:
        response = ""
        context_length = str(context_num * self.context_size)

        cmd = [
            LLAMA_RUN_PATH,
            "--context-size", context_length,
            MISTRAL_MODEL_PATH,
            prompt
        ]

        print(f"[LLAMA] Number of Tokens     ({self.count_tokens(prompt)}): {repr(prompt)}")

        try:
            output = subprocess.check_output(cmd, text=True).strip()
            response += output
        except subprocess.CalledProcessError:
            pass
        return response

