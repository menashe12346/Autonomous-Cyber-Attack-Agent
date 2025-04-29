from blackboard.blackboard import initialize_blackboard

class ScenarioOrchestrator:
    """
    Manages the execution of a penetration testing scenario.

    This class controls:
    - Blackboard initialization per scenario
    - AgentManager coordination
    - Looping through steps
    - Stop conditions enforcement
    """

    def __init__(self, blackboard, agent_manager, target, max_steps=20, scenario_name="DefaultScenario", stop_conditions=None):
        """
        Initialize the orchestrator with simulation parameters.

        Args:
            blackboard: BlackboardAPI instance.
            agent_manager: AgentManager instance.
            target (str): Target IP address.
            max_steps (int): Maximum number of steps to execute.
            scenario_name (str): Human-readable name of the scenario.
            stop_conditions (list): Optional list of callables taking blackboard dict and returning True if scenario should stop.
        """
        self.blackboard = blackboard
        self.agent_manager = agent_manager
        self.max_steps = max_steps
        self.current_step = 0
        self.scenario_name = scenario_name
        self.stop_conditions = stop_conditions or []
        self.active = False
        self.target = target

    def start(self):
        """
        Initialize blackboard values and mark scenario as active.
        Resets internal step counter and blackboard state.
        """
        self.current_step = 0
        self.active = True

        # Initialize target structure
        self.blackboard.blackboard = initialize_blackboard(self.target)
        print(f"self.blackboard.blackboard: {self.blackboard.blackboard}")

        print(f"[+] Starting scenario: {self.scenario_name}")

    def should_continue(self):
        """
        Check whether scenario should continue based on conditions.

        Returns:
            bool: True if scenario should continue, False if it should stop.
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
        Execute a single simulation step by running the next eligible agent.
        """
        print(f"[>] Running step {self.current_step}...")
        self.agent_manager.run_step()
        self.current_step += 1

    def end(self):
        """
        Mark scenario as ended and print completion message.
        """
        self.active = False
        print(f"[+] Scenario '{self.scenario_name}' ended after {self.current_step} steps.")

    def run_scenario_loop(self):
        """
        Run full scenario loop from start to end.
        """
        self.start()
        while self.should_continue():
            self.step()
        self.end()
