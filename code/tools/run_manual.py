import subprocess

def run_clean_output(cmd, timeout=600):
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    full_output = []

    try:
        for line in process.stdout:
            print(line, end="")  # print in real time
            full_output.append(line.rstrip())

        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        raise TimeoutError(f"Command exceeded timeout of {timeout} seconds")

    return "\n".join(full_output)

# [DEBUG]
if __name__ == "__main__":
    print("🔥 run_manual.py started")
    try:
        output = run_clean_output(
            ["msfconsole", "-q", "-x", "use exploit/unix/ftp/vsftpd_234_backdoor"],
            timeout=60
        )
        print("\n✅ output: \n")
        print(output)
    except TimeoutError as e:
        print(f"❌ Timeout: {e}")

# Check if port 6200 is used:
# sudo netstat -plant | grep :6200