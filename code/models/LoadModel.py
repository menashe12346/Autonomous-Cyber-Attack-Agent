import subprocess
import os

class LoadModel:
    def __init__(self, llama_path, model_path, tokens=4096, threads=8, n_batch=4096):
        self.llama_path = llama_path
        self.model_path = model_path
        self.tokens = str(tokens)
        self.threads = str(threads)
        self.n_batch = str(n_batch)

        if not os.path.isfile(self.llama_path):
            raise FileNotFoundError(f"llama-run binary not found: {self.llama_path}")
        if not self.model_path.startswith("file://"):
            raise ValueError("model_path must start with 'file://'")

        print("✅ LoadModel initialized successfully.")
    
    def run_prompt(self, prompt):
        cmd = [
            self.llama_path,
            self.model_path,
            prompt,
            "-n", self.tokens,
            "-t", self.threads,
            "--n-batch", self.n_batch,
            "--ctx-size", "4096",
        ]
        try:
            output = subprocess.check_output(cmd, text=True)
            return output.strip()
        except subprocess.CalledProcessError as e:
            print("❌ llama-run failed:")
            print(e.output)
            return None


    def run_prompts(self, prompts):
        responses = []
        context = ""
        for prompt in prompts:
            full_prompt = context + "\n" + prompt if context else prompt
            cmd = [
                self.llama_path,
                self.model_path,
                full_prompt,
                "-n", self.tokens,
                "-t", self.threads,
                "--n-batch", self.n_batch,
                "--ctx-size", "4096",
            ]
            try:
                output = subprocess.check_output(cmd, text=True)
                responses.append(output)
                context += f"\n{prompt}\n{output.strip()}"
            except subprocess.CalledProcessError as e:
                print("❌ llama-run failed:")
                print(e.output)
                responses.append(None)
        return responses
