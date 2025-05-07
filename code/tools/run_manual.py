import subprocess

def run_clean_output(cmd, timeout=600):
    """
    מריץ פקודת shell, שומר את כל הפלט למשתנה, מחזיר אותו.
    מציג פלט בזמן אמת.
    """
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
            print(line, end="")  # הדפסה בזמן אמת
            full_output.append(line.rstrip())

        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        raise TimeoutError(f"Command exceeded timeout of {timeout} seconds")

    return "\n".join(full_output)

# שימוש
if __name__ == "__main__":
    print("🔥 run_manual.py started")
    try:
        output = run_clean_output(
            ["msfconsole", "-q", "-x", "use exploit/unix/ftp/vsftpd_234_backdoor"],
            timeout=60
        )
        print("\n✅ פלט שנשמר למשתנה:\n")
        print(output)
    except TimeoutError as e:
        print(f"❌ Timeout: {e}")

# sudo netstat -plant | grep :6200