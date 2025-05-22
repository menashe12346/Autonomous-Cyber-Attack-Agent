import os
import sys
import json
import time
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import torch.nn as nn

from config import (
    TARGET_IP,
    DATASET_NVD_CVE_PATH,
    DATASET_OS_LINUX, DATASET_OS_LINUX_KERNEL,
    DATASET_METASPLOIT, DATASET_EXPLOITDB_CVE_EXPLOIT_PATH, DATASET_EXPLOIT
)
from blackboard.blackboard import initialize_blackboard
from blackboard.api import BlackboardAPI
from agents.agent_manager import AgentManager
from agents.recon_agent import ReconAgent
from agents.vuln_agent import VulnAgent
from agents.exploit_agent import ExploitAgent
from orchestrator.scenario_orchestrator import ScenarioOrchestrator
from models.policy_model import PolicyModel
from models.llm.llama_interface import LlamaModel
from encoders.state_encoder import StateEncoder
from encoders.action_encoder import ActionEncoder
from tools.action_space import get_commands_for_agent
from utils.utils import load_dataset
from create_datasets.create_exploit_dataset.create_full_exploit_dataset import merge_exploit_datasets

BLACKBOARD_PATH = "blackboard/blackboard.json"
REFRESH_INTERVAL = 0.2  # seconds

class GuiStdout:
    """
    Redirects stdout and stderr writes to the GUI log,
    but only after detecting a line starting with '[ExploitAgent]'.
    Also tees everything back out to the real terminal.
    """
    def __init__(self, log_func, target_prefix="[ExploitAgent]", tag=None):
        self.log = log_func
        self.tag = tag
        self.target_prefix = target_prefix
        self.capturing = False
        self.success_detected = False
        # keep a handle on the real stdout/stderr so we can still write to the console
        self._orig_stdout = sys.__stdout__
        self._orig_stderr = sys.__stderr__

    def write(self, msg):
        # Always forward everything to the real terminal
        try:
            self._orig_stdout.write(msg)
        except Exception:
            pass
        
        if "Attack Executed Successfully" in msg:
            self.log("\033[38;5;208mAttack Executed Successfully\033[0m", self.tag)
            self.success_detected = True
            return

        # Now filter for GUI logging
        for line in msg.splitlines():
            text = line.rstrip()
            if not text:
                continue
            if not self.capturing:
                if text.startswith(self.target_prefix):
                    self.capturing = True
                    self.log(text, self.tag)
            else:
                self.log(text, self.tag)

    def flush(self):
        # flush both the real streams
        try:
            self._orig_stdout.flush()
        except Exception:
            pass
        try:
            self._orig_stderr.flush()
        except Exception:
            pass

class CyberMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🛡️ Cyber Attack Monitor")
        self.root.geometry("960x700")
        self.root.configure(bg="#1e1e1e")

        # IP input frame
        ip_frame = tk.Frame(root, bg="#1e1e1e")
        ip_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(
            ip_frame,
            text="Target IP:",
            font=("Arial", 12),
            bg="#1e1e1e",
            fg="white"
        ).pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(
            ip_frame,
            font=("Arial", 12),
            width=20
        )
        self.ip_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.ip_entry.insert(0, TARGET_IP)

        # Logs display
        self.text_area = ScrolledText(
            root, font=("Consolas", 11), bg="#121212", fg="#33FF33", wrap=tk.WORD
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Start button
        self.start_btn = tk.Button(
            root,
            text="▶ Start Attack",
            font=("Arial", 14), bg="#4CAF50", fg="white",
            command=self.start
        )
        self.start_btn.pack(pady=(0, 10))

        self.last_state = {}
        self.running = False
        self.text_area.tag_config("vuln", foreground="#FF5555", font=("Consolas", 12, "bold"))

    def log(self, msg, tag=None):
        if tag:
            self.text_area.insert(tk.END, msg + "\n", tag)
        else:
            self.text_area.insert(tk.END, msg + "\n")
        self.text_area.see(tk.END)

    def start(self):
        self.target_ip = self.ip_entry.get().strip()
        if not self.target_ip:
            self.log("[!] Please enter a valid Target IP.")
            return
        self.start_btn.config(state=tk.DISABLED)
        self.running = True
        threading.Thread(target=self.watch_blackboard, daemon=True).start()
        threading.Thread(target=self.run_simulation, daemon=True).start()

    def watch_blackboard(self):
        if os.path.exists(BLACKBOARD_PATH):
            try:
                with open(BLACKBOARD_PATH, 'r') as f:
                    self.last_state = json.load(f)
            except:
                self.last_state = {}
        while self.running:
            try:
                with open(BLACKBOARD_PATH, 'r') as f:
                    current = json.load(f)
                self.detect_changes(self.last_state, current)
                self.last_state = current
            except Exception as e:
                self.log(f"[!] Monitor Error: {e}")
            time.sleep(REFRESH_INTERVAL)

    def detect_changes(self, old, new, prefix=""):
        if isinstance(new, dict):
            for key, val in new.items():
                if key == "cpes": continue
                path = f"{prefix}.{key}" if prefix else key
                if key not in old:
                    self.describe_addition(path, val)
                else:
                    self.detect_changes(old.get(key, {}), val, path)
        elif isinstance(new, list):
            if prefix.endswith("cpes"): return
            for item in new:
                if item not in (old if isinstance(old, list) else []):
                    self.describe_addition(prefix, item)
        else:
            if old != new:
                self.log(f"🔄 Updated '{prefix}' to {new}")

    def describe_addition(self, path, value):
        if path.endswith("cpes") or ".cpes" in path or value in (None, "", "NO"):
            return
        if path.startswith("target.services") and isinstance(value, dict):
            port = value.get("port", "?")
            proto = value.get("protocol", "?")
            svc = value.get("service", "unknown")
            ver = value.get("server_version")
            msg = f"📡 Open Port: {port}/{proto} running service '{svc}'"
            if ver and ver not in ("", "NO"):
                msg += f" version {ver}"
            self.log(msg)
            return
        if "target.os.distribution.name" in path:
            distro = value
            ver = self.last_state.get("target", {}).get("os", {}).get("distribution", {}).get("version")
            if distro and distro != "NO":
                self.log(f"🖥️ OS: {distro}{(' ' + ver) if ver and ver != 'NO' else ''}")
            return
        if "target.os.kernel" in path and value and value != "NO":
            self.log(f"🧠 Kernel: {value}")
            return
        if path.endswith("vulnerabilities_found") and isinstance(value, list) and value:
            self.log("\n❗ Vulnerabilities Detected:", tag="vuln")
            for entry in value:
                cve = entry.get("cve", "N/A")
                score = entry.get("cvss", "-")
                self.log(f"   • {cve} (CVSS {score})", tag="vuln")
            return
        self.log(f"➕ {path}: {value}")

    def run_simulation(self):
        # Redirect stdout/stderr to capture ExploitAgent logs (and tee back to console)
        captured_out = GuiStdout(self.log)
        sys.stdout = captured_out
        sys.stderr = captured_out

        self.log("🚀 Running Cyber Attack Simulation...")
        try:
            import torch
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        except:
            device = None

        # Load datasets
        cves = load_dataset(DATASET_NVD_CVE_PATH)
        msf = load_dataset(DATASET_METASPLOIT)
        edb = load_dataset(DATASET_EXPLOITDB_CVE_EXPLOIT_PATH)
        os_linux = load_dataset(DATASET_OS_LINUX)
        os_kernel = load_dataset(DATASET_OS_LINUX_KERNEL)
        full_exp = merge_exploit_datasets(msf, edb, DATASET_EXPLOIT)

        # Initialize agents and orchestrator
        model = LlamaModel()
        bb = initialize_blackboard(self.target_ip)
        api = BlackboardAPI(bb)

        # Patch update_state to persist to file
        orig_update = api.update_state
        def patched_update(agent, state):
            orig_update(agent, state)
            with open(BLACKBOARD_PATH, 'w') as f:
                json.dump(api.blackboard, f, indent=2)
        api.update_state = patched_update

        recon_cmds = get_commands_for_agent("recon")
        recon_model = PolicyModel(1024, len(recon_cmds)).to(device)
       # טען כאן את המשקלים ששמרת ב-train
        recon_model.load_state_dict(
           torch.load("models/saved_models/recon_model.pth", map_location=device)
        )
        recon_model.eval()

        recon_agent = ReconAgent(
            api,
            recon_model,
            None, StateEncoder(recon_cmds), ActionEncoder(recon_cmds),
            {}, model, 0.0, os_linux, os_kernel
        )

        vuln_agent = VulnAgent(api, cves, 0.0, os_linux, os_kernel, msf)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        exploit_cmds = list({v["cve"] for v in msf if "cve" in v})


        exploit_model = PolicyModel(1024, len(exploit_cmds)).to(device)
        # ופה טען גם את משקלי ה-exploit agent
        exploit_model.load_state_dict(
            torch.load("models/saved_models/exploit_model.pth", map_location=device)
        )
        exploit_model.eval()

        exploit_agent = ExploitAgent(
            blackboard_api=api,
            replay_buffer=None,
            policy_model=exploit_model,
            state_encoder=StateEncoder(exploit_cmds),
            action_encoder=ActionEncoder(exploit_cmds),
            command_cache={},
            model=model,
            epsilon=0.0,
            metasploit_dataset=msf,
            exploitdb_dataset=edb,
            full_exploit_dataset=full_exp,
            os_linux_dataset=os_linux,
            os_linux_kernel_dataset=os_kernel
        )

        mgr = AgentManager(api)
        mgr.register_agents([recon_agent, vuln_agent, exploit_agent])
        orch = ScenarioOrchestrator(api, mgr, "EvaluationEpisode", self.target_ip)

        self.log("[*] Starting scenario loop step-by-step...")

        while True:
            orch.step()
            """
            # 🔍 DEBUG: show ReconAgent’s top-5 action probabilities
            with torch.no_grad():
                # 1. קבל את היסטוריית הפעולות (או [] אם אין)
                actions_hist = getattr(recon_agent, "actions_history", [])
                # 2. קודד את ה-state + היסטוריה והוסף ממד batch
                state_tensor = recon_agent.state_encoder.encode(api.blackboard, actions_hist)
                state_tensor = state_tensor.unsqueeze(0)        # shape: [1, feature_dim]
                # 3. הפעל קדימה בחלק ה-policy
                logits = recon_model(state_tensor)               # shape: [1, num_actions]
                probs  = torch.softmax(logits, dim=-1)[0]       # shape: [num_actions]
                # 4. בחר את 5 הפעולות המובילות
                top_vals, top_idxs = probs.topk(5)              # שני טנסורים בגודל [5]
                flat_idxs = top_idxs.tolist()                   # רשימת int
                flat_vals = top_vals.tolist()                   # רשימת float
                # 5. הדפס ל-GUI
                self.log("🔍 Recon top5:", None)
                for idx, p in zip(flat_idxs, flat_vals):
                    cmd = recon_cmds[idx]
                    self.log(f"   • {cmd} — p={p:.3f}")
            """

            # בדיקה אם יש הצלחה במצב ה־blackboard
            current_state = api.blackboard
            attack_impact = current_state.get("ExploitAgent", {}).get("attack_impact", {})

            # ככה תעצור ברגע שמצאת את ההודעה
            if captured_out.success_detected:
                break

            time.sleep(REFRESH_INTERVAL)


        self.log("\n✅ Simulation Completed!", tag="vuln")
        # שיחזור של ערוצי הפלט המקוריים
        sys.stdout = captured_out._orig_stdout
        sys.stderr = captured_out._orig_stderr

if __name__ == "__main__":
    root = tk.Tk()
    app = CyberMonitorApp(root)
    root.mainloop()
