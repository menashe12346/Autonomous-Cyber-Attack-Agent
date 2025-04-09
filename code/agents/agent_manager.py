class AgentManager:
    def __init__(self, blackboard_api):
        self.agents = []
        self.blackboard = blackboard_api
        self.current_index = 0
        self.execution_log = []
        self.actions_history = []  # רשימה שתשמור את כל הפעולות שבוצעו במערכת

    def register_agents(self, agent_list):
        """
        מקבל רשימת סוכנים ומריץ תהליך רישום.
        """
        self.agents = agent_list
        self.current_index = 0
        self.execution_log.clear()

    def run_all(self):
        """
        מריץ את כל הסוכנים ש־should_run שלהם מחזיר True.
        """
        for agent in self.agents:
            if agent.should_run():
                agent.run()
                self.execution_log.append(agent.name)
                self.actions_history.append(agent.last_action)

    def run_step(self):
        """
        מריץ את הסוכן הבא בתור אם הוא מוכן לפעולה.
        """
        if not self.agents:
            return

        agent = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)

        if agent.should_run():
            agent.run()
            self.execution_log.append(agent.name)
            self.actions_history.append(agent.last_action)

    def has_pending_actions(self):
        """
        בודק אם יש סוכנים שעדיין עשויים לפעול.
        """
        return any(agent.should_run() for agent in self.agents)

    def log_summary(self):
        """
        מציג את רשימת הסוכנים שפעלו עד כה.
        """
        print("Agents executed in this round:")
        for name in self.execution_log:
            print(f"✅ {name}")
            print(self.actions_history)
