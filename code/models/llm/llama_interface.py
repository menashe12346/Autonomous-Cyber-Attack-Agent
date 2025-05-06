import os
import subprocess
import tiktoken

from models.llm.base_llm import BaseLLM

class LlamaModel(BaseLLM):
    """
    LLM interface for executing prompts using llama.cpp binary.
    Supports single or multiple prompts with contextual memory.
    """

    def __init__(self, llama_path, model_path, tokens=4000, threads=8, n_batch=8192, context_size=8192):
        self.llama_path = llama_path
        self.model_path = model_path
        self.tokens = str(tokens)
        self.threads = str(threads)
        self.n_batch = str(n_batch)
        self.context_size= str(context_size)

        if not os.path.isfile(self.llama_path):
            raise FileNotFoundError(f"llama-run binary not found: {self.llama_path}")
        if not self.model_path.startswith("file://"):
            raise ValueError("model_path must start with 'file://'")
        
        print("✅ Llama Model initialized successfully.")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string using cl100k_base tokenizer.
        """
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))

    def run(self, prompts: list[str], context_num = 1) -> list[str]:
        responses = []
        context = ""
        context_length = str(context_num * 9999)

        for prompt in prompts:
            full_prompt = (context + "\n" + prompt) if context else prompt

            cmd = [
                "/mnt/linux-data/project/code/models/llama.cpp/build/bin/llama-run",
                "--context-size", context_length,
                "/mnt/linux-data/project/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf",
                full_prompt
            ]

            print(f"[LLAMA] Full Tokens     ({self.count_tokens(full_prompt)}): {repr(full_prompt)}")

            try:
                output = subprocess.check_output(cmd, text=True).strip()
                responses.append(output)
                context += f"\n{prompt}\n{output}"
            except subprocess.CalledProcessError:
                responses.append("")
        return responses

