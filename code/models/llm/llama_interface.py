import os
import subprocess
import tiktoken

from models.llm.base_llm import BaseLLM
from utils.utils import one_line


class LlamaModel(BaseLLM):
    """
    LLM interface for executing prompts using llama.cpp binary.
    Supports single or multiple prompts with contextual memory.
    """

    def __init__(self, llama_path, model_path, tokens=3500, threads=4, n_batch=8192, context_size=500):
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

    def run(self, prompts: list[str]) -> list[str]:
        """
        Run one or more prompts in sequence, maintaining conversational context.
        For a single prompt, just call run([prompt]).

        Args:
            prompts (list[str]): List of prompt strings.

        Returns:
            list[str]: List of model outputs, one per prompt.
        """
        responses = []
        context = ""

        for prompt in prompts:
            full_prompt = context + "\n" + prompt if context else prompt

            # === Debug Output ===
            print(f"[LLAMA] Prompt Tokens   ({self.count_tokens(prompt)}): {repr(prompt)}")
            print(f"[LLAMA] Context Tokens  ({self.count_tokens(context)}): {repr(context)}")
            print(f"[LLAMA] Full Tokens     ({self.count_tokens(full_prompt)}): {repr(full_prompt)}")

            cmd = [
                self.llama_path,
                self.model_path,
                full_prompt,
                "-n", self.tokens,
                "-t", self.threads,
                "--n-batch", self.n_batch,
                "--ctx-size", self.context_size,
            ]

            try:
                output = subprocess.check_output(cmd, text=True).strip()
                responses.append(output)
                context += f"\n{prompt}\n{one_line(output)}"
            except subprocess.CalledProcessError:
                responses.append("")

        return responses
