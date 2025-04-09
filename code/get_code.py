import os, re, tiktoken

def remove_docstrings(text):
    return re.sub(r'""".*?"""', '', text, flags=re.DOTALL)

def minify_line(line):
    line = re.sub(r'#.*', '', line)              # הסרת הערות
    line = re.sub(r'\s+', ' ', line)             # איחוד רווחים
    line = line.strip()
    if not line:
        return ''
    line = re.sub(r'\s*([=:+\-*/(),<>])\s*', r'\1', line)  # צמצום סביב סימנים
    return line

def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")  # מתאים ל-GPT-4o
    return len(enc.encode(text, disallowed_special=()))

def print_all_python_files(start_dir, output_file):
    output = ''
    for root, _, files in os.walk(start_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        raw = f.read()
                        raw = remove_docstrings(raw)
                        lines = raw.split('\n')
                        clean = [minify_line(l) for l in lines]
                        compact = ';'.join([l for l in clean if l])
                        output += f"<<{path}>>{compact};"
                except:
                    pass

    # כתיבה לקובץ
    with open(output_file, 'w', encoding='utf-8') as out_f:
        out_f.write(output)

    print(f"[Total Tokens (GPT-4o): {count_tokens(output)}]")
    print(f"[Saved to: {output_file}]")

# הפעלת הסקריפט
print_all_python_files(
    "/mnt/linux-data/project/code",
    "/mnt/linux-data/project/code/code.txt"
)
