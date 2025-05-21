import os
import json
import time
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

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

class CyberMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🛡️ Cyber Attack Monitor")
        self.root.geometry("960x650")
        self.root.configure(bg="#1e1e1e")

        # Logs display
        self.text_area = ScrolledText(root, font=("Consolas", 11), bg="#121212", fg="#33FF33", wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Start button
        self.start_btn = tk.Button(
            root,
            text="▶ Start Simulation",
            font=("Arial", 14), bg="#4CAF50", fg="white",
            command=self.start
        )
        self.start_btn.pack(pady=10)

        self.last_state = {}
        self.running = False

        # Highlight tag for vulnerabilities
        self.text_area.tag_config("vuln", foreground="#FF5555", font=("Consolas", 12, "bold"))

    def log(self, msg, tag=None):
        if tag:
            self.text_area.insert(tk.END, msg + "\n", tag)
        else:
            self.text_area.insert(tk.END, msg + "\n")
        self.text_area.see(tk.END)

    def start(self):
        # Prevent multiple starts
        self.start_btn.config(state=tk.DISABLED)
        self.running = True
        # Launch monitoring thread
        threading.Thread(target=self.watch_blackboard, daemon=True).start()
        # Launch simulation thread
        threading.Thread(target=self.run_simulation, daemon=True).start()

    def watch_blackboard(self):
        # Load initial state
        if os.path.exists(BLACKBOARD_PATH):
            try:
                with open(BLACKBOARD_PATH, 'r') as f:
                    self.last_state = json.load(f)
            except:
                self.last_state = {}

        # Continuous watch loop
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
                # Skip CPEs entirely
                if key == "cpes":
                    continue
                path = f"{prefix}.{key}" if prefix else key
                if key not in old:
                    self.describe_addition(path, val)
                else:
                    self.detect_changes(old.get(key, {}), val, path)

        elif isinstance(new, list):
            # Skip if this list is CPEs
            if prefix.endswith("cpes"):
                return
            old_list = old if isinstance(old, list) else []
            for item in new:
                if item not in old_list:
                    self.describe_addition(prefix, item)

        else:
            if old != new:
                self.log(f"🔄 Updated '{prefix}' to {new}")

    def describe_addition(self, path, value):
        # Skip printing any CPE entries
        if path.endswith("cpes") or ".cpes" in path:
            return

        # Open ports
        if path.startswith("target.services") and isinstance(value, dict):
            port = value.get("port", "?")
            proto = value.get("protocol", "?")
            svc = value.get("service", "unknown")
            ver = value.get("server_version", "-")
            self.log(f"📡 Open Port: {port}/{proto} running service '{svc}' version {ver}")
            return

        # OS distribution
        if "target.os.distribution.name" in path:
            distro = value or "Unknown"
            ver = self.last_state.get("target", {}).get("os", {}).get("distribution", {}).get("version", "-")
            self.log(f"🖥️ OS: {distro} {ver}")
            return

        # Kernel
        if "target.os.kernel" in path:
            self.log(f"🧠 Kernel: {value}")
            return

        # Vulnerabilities
        if path.endswith("vulnerabilities_found") and isinstance(value, list):
            self.log("\n❗ Vulnerabilities Detected:", tag="vuln")
            for entry in value:
                cve = entry.get("cve", "N/A")
                score = entry.get("cvss", "-")
                self.log(f"   • {cve} (CVSS {score})", tag="vuln")
            return

        # Generic additions
        self.log(f"➕ {path}: {value}")

    def run_simulation(self):
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

        model = LlamaModel()
        bb = initialize_blackboard(TARGET_IP)
        api = BlackboardAPI(bb)

        # Patch update_state to save file
        original_update = api.update_state
        def patched_update(agent, state):
            original_update(agent, state)
            with open(BLACKBOARD_PATH, 'w') as f:
                json.dump(api.blackboard, f, indent=2)
        api.update_state = patched_update

        # Create agents
        recon_cmds = get_commands_for_agent("recon")
        recon_agent = ReconAgent(
            api,
            policy_model=PolicyModel(1024, len(recon_cmds)).to(device) if device else None,
            replay_buffer=None,
            state_encoder=StateEncoder(recon_cmds),
            action_encoder=ActionEncoder(recon_cmds),
            command_cache={}, model=model, epsilon=0.0,
            os_linux_dataset=os_linux, os_linux_kernel_dataset=os_kernel
        )
        vuln_agent = VulnAgent(api, cves, 0.0, os_linux, os_kernel, msf)
        exploit_cmds = [e['cve'] for e in msf if 'cve' in e]
        exploit_agent = ExploitAgent(
            api,
            policy_model=PolicyModel(1024, len(exploit_cmds)).to(device) if device else None,
            replay_buffer=None,
            state_encoder=StateEncoder(exploit_cmds),
            action_encoder=ActionEncoder(exploit_cmds),
            command_cache={}, model=model, epsilon=0.0,
            metasploit_dataset=msf, exploitdb_dataset=edb, full_exploit_dataset=full_exp,
            os_linux_dataset=os_linux, os_linux_kernel_dataset=os_kernel
        )

        # Register and run
        mgr = AgentManager(api)
        mgr.register_agents([recon_agent, vuln_agent, exploit_agent])
        orch = ScenarioOrchestrator(api, mgr, "EvaluationEpisode", TARGET_IP)
        orch.run_scenario_loop()

        self.log("\n✅ Simulation Completed!", tag="vuln")

if __name__ == "__main__":
    root = tk.Tk()
    app = CyberMonitorApp(root)
    root.mainloop()
