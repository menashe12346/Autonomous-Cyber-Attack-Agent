class ScenarioOrchestrator:
    def __init__(self, blackboard, agent_manager, target, max_steps=20, scenario_name="DefaultScenario", stop_conditions=None):
        self.blackboard = blackboard
        self.agent_manager = agent_manager
        self.max_steps = max_steps
        self.current_step = 0
        self.scenario_name = scenario_name
        self.stop_conditions = stop_conditions or []
        self.active = False
        self.target=target

    def start(self):
        """
        מאתחל את התרחיש: איפוס מדדים, לוגים, איתחול Blackboard ו־AgentManager.
        """
        self.current_step = 0
        self.active = True
        self.blackboard.blackboard["target"] = {
            "ip": self.target,
            "os": "Unknown",
            "services": [
                {"port": "", "protocol": "", "service": ""},
                {"port": "", "protocol": "", "service": ""},
                {"port": "", "protocol": "", "service": ""}
            ]
        }
        self.blackboard.blackboard["web_directories_status"] = {
            "404": { "": "" },
            "200": { "": "" },
            "403": { "": "" },
            "401": { "": "" },
            "503": { "": "" }
        }

        """
        self.blackboard.blackboard["attack_id"] = self.scenario_name
        self.blackboard.blackboard["actions_log"] = []
        self.blackboard.blackboard["reward_log"] = []
        self.blackboard.blackboard["errors"] = []
        self.blackboard.blackboard["timestamps"]["first_packet"] = None
        self.blackboard.blackboard["timestamps"]["last_packet"] = None
        self.blackboard.blackboard["runtime_behavior"] = {
            "shell_opened": {
                "shell_type": "",
                "session_type": "",
                "shell_access_level": "",
                "authentication_method": "",
                "shell_session": { "commands_run": [] }
            }
        }
        """
        print(f"[+] Starting scenario: {self.scenario_name}")

    def should_continue(self):
        """
        בודק האם יש להמשיך את התרחיש או להפסיק אותו לפי תנאים שהוגדרו.
        """
        if not self.active:
            return False
        if self.current_step >= self.max_steps:
            print("[!] Max steps reached.")
            return False
        for condition in self.stop_conditions:
            if condition(self.blackboard.blackboard):
                print("[!] Stop condition met.")
                return False
        return True

    def step(self):
        """
        מבצע צעד אחד של הסימולציה ע"י הפעלת AgentManager.
        """
        print(f"[>] Running step {self.current_step}...")
        self.agent_manager.run_step()
        self.current_step += 1

    def end(self):
        """
        סוגר את התרחיש ומסמן את הסימולציה כלא פעילה.
        """
        self.active = False
        #self.blackboard.blackboard["timestamps"]["last_packet"] = self.current_step
        print(f"[+] Scenario '{self.scenario_name}' ended after {self.current_step} steps.")

    def run_scenario_loop(self):
        """
        מפעיל את כל התרחיש בלולאה עד לסיום.
        """
        self.start()
        while self.should_continue():
            self.step()
        self.end()
