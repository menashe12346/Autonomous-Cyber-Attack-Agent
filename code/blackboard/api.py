import time
import copy

class BlackboardAPI:
    """
    Provides controlled access and updates to a shared blackboard dictionary.
    This class is used by agents to retrieve and modify the shared state.
    """

    def __init__(self, blackboard_dict: dict):
        """
        Initialize the API with an external blackboard dictionary.

        Args:
            blackboard_dict (dict): A dictionary representing the shared state.
        """
        self.blackboard = blackboard_dict

    def get_state_for_agent(self, agent_name: str) -> dict:
        """
        Return a deep copy of the current blackboard state for agent use.

        Args:
            agent_name (str): Name of the agent requesting the state.

        Returns:
            dict: A deep copy of the current state.
        """
        return copy.deepcopy(self.blackboard)

    def update_runtime_behavior(self, info_dict: dict):
        """
        Update or merge runtime_behavior fields in the blackboard.

        Args:
            info_dict (dict): Runtime keys and values to update.
        """
        runtime = self.blackboard.setdefault("runtime_behavior", {})

        for key, value in info_dict.items():
            if isinstance(value, list):
                existing = runtime.get(key, [])
                runtime[key] = list(set(existing + value))
            elif isinstance(value, dict):
                existing = runtime.get(key, {})
                if not isinstance(existing, dict):
                    existing = {}
                existing.update(value)
                runtime[key] = existing
            else:
                runtime[key] = value

    def append_action_log(self, entry: dict):
        """
        Append an action entry to the action log with a timestamp.

        Args:
            entry (dict): The action log entry to append.
        """
        entry["timestamp"] = time.time()
        self.blackboard.setdefault("actions_log", []).append(entry)

    def record_reward(self, action: str, reward: float):
        """
        Record a reward event for the last action taken.

        Args:
            action (str): The action associated with the reward.
            reward (float): The reward value.
        """
        entry = {
            "action": action,
            "reward": reward,
            "timestamp": time.time()
        }
        self.blackboard.setdefault("reward_log", []).append(entry)

    def add_error(self, agent: str, action: str, error: str):
        """
        Record an error that occurred during an agent's action.

        Args:
            agent (str): The name of the agent.
            action (str): The action that caused the error.
            error (str): The error message.
        """
        entry = {
            "agent": agent,
            "action": action,
            "error": error,
            "timestamp": time.time()
        }
        self.blackboard.setdefault("errors", []).append(entry)

    def get_last_actions(self, agent: str, n: int = 5):
        """
        Retrieve the last N actions performed by a specific agent.

        Args:
            agent (str): The agent name.
            n (int): Number of past actions to retrieve.

        Returns:
            list: List of recent action log entries.
        """
        return [
            log for log in reversed(self.blackboard.get("actions_log", []))
            if log.get("agent") == agent
        ][:n]

    def update_target_services(self, new_services: list):
        """
        Add new services to the target.services list if not already present.

        Args:
            new_services (list): List of service dicts to add.
        """
        existing = self.blackboard["target"].get("services", [])
        for service in new_services:
            if service not in existing:
                existing.append(service)

    def update_exploit_metadata(self, exploit_data: dict):
        """
        Update the metadata block about the selected exploit.

        Args:
            exploit_data (dict): Dictionary of exploit metadata to update.
        """
        self.blackboard["exploit_metadata"].update(exploit_data)

    def overwrite_blackboard(self, new_state: dict):
        """
        Overwrite the blackboard with a new state dictionary.

        Notes:
        - Completely clears the previous blackboard.
        - Does NOT preserve transient fields like 'actions_history'.

        Args:
            new_state (dict): The new state to replace the old one.
        """
        if not isinstance(new_state, dict):
            raise ValueError("new_state must be a dictionary")

        self.blackboard.clear()
        self.blackboard.update(new_state)