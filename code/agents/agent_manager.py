class AgentManager:
    """
    Manages the lifecycle and execution of multiple agents within an attack scenario.
    Supports agent registration, turn-based or full execution, logging, and pending checks.
    """

    def __init__(self, blackboard_api):
        """
        Initialize the AgentManager with access to the shared blackboard.

        Args:
            blackboard_api: Instance of BlackboardAPI for shared state.
        """
        self.agents = []
        self.blackboard = blackboard_api
        self.current_index = 0
        self.execution_log = []
        self.actions_history = []

    def register_agents(self, agent_list):
        """
        Register a new list of agents and reset execution state.

        Args:
            agent_list (list): List of agent instances to register.
        """
        self.agents = agent_list
        self.current_index = 0
        self.execution_log.clear()
        self.actions_history.clear()

    def run_all(self):
        """
        Run all agents whose `should_run()` method returns True.
        """
        for agent in self.agents:
            if agent.should_run():
                agent.run()
                self.execution_log.append(agent.name)
                self.actions_history.append(agent.last_action)

    def run_step(self):
        """
        Run the next agent in a round-robin fashion if it's ready to act.
        """
        if not self.agents:
            return

        agent = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)

        if agent.should_run():
            agent.run()
            self.execution_log.append(agent.name)
            self.actions_history.append(agent.last_action)

    def has_pending_actions(self) -> bool:
        """
        Check if any registered agent is still eligible to act.

        Returns:
            bool: True if at least one agent should run, otherwise False.
        """
        return any(agent.should_run() for agent in self.agents)

    def log_summary(self):
        """
        Print a summary of which agents executed in the last round.
        """
        print("Agents executed in this round:")
        for name in self.execution_log:
            print(f"- {name}")
        print("Executed actions:")
        for action in self.actions_history:
            print(f"  → {action}")

    def run_recon_only_step(self):
        for agent in self.agents:
            if agent.name.lower().startswith("recon") and agent.should_run():
                agent.run()

    def run_vuln_and_exploit_step(self):
        for agent in self.agents:
            if agent.name.lower().startswith("vuln") and agent.should_run():
                agent.run()

        for agent in self.agents:
            if agent.name.lower().startswith("exploit") and agent.should_run():
                for i in range(2):
                    agent.run()
