import os, tiktoken

def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")  # מתאים ל-GPT-4o
    return len(enc.encode(text, disallowed_special=()))

def print_all_python_files(start_dir, output_file):
    skip_dirs = {
        "llama.cpp",
        "nous-hermes",
        "__pycache__",
        "models--google--flan-t5-xl"
    }

    output = ''
    for root, dirs, files in os.walk(start_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        snippet = f"<<{path}>>\n{content}\n"
                        output += snippet
                        print(snippet)
                except Exception as e:
                    print(f"[ERROR] Failed to read {path}: {e}")

    with open(output_file, 'w', encoding='utf-8') as out_f:
        out_f.write(output)

    print(f"\n[Total Tokens (GPT-4o): {count_tokens(output)}]")
    print(f"[Saved to: {output_file}]")

# הפעלת הסקריפט
print_all_python_files(
    "/mnt/linux-data/project/code",
    "/mnt/linux-data/project/code/code.txt"
)
