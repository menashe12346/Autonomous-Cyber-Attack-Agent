import time
import copy
import json

from config import BLACKBOARD_PATH
from utils.state_check.state_sorting import sort_state
from utils.state_check.state_validator import validate_state

class BlackboardAPI:
    """
    Provides controlled access and updates to a shared blackboard dictionary.
    This class is used by agents to retrieve and modify the shared state.
    """

    def __init__(self, blackboard_dict: dict, json_path: str = BLACKBOARD_PATH):
        """
        Initialize the API with an external blackboard dictionary.

        Args:
            blackboard_dict (dict): A dictionary representing the shared state.
        """
        self.blackboard = blackboard_dict
        self.json_path = json_path
        self._save_to_file()
    
    def fill_state(self, actions_history: dict):
        self.blackboard["actions_history"] = actions_history.copy()
        self.blackboard["cpes"] = []
        self.blackboard["vulnerabilities_found"] = []
    
    def get_state_for_agent(self, agent_name: str) -> dict:
        """
        Return a deep copy of the current blackboard state for agent use.

        Args:
            agent_name (str): Name of the agent requesting the state.

        Returns:
            dict: A deep copy of the current state.
        """
        return copy.deepcopy(self.blackboard)

    def append_action_log(self, entry: dict):
        """
        Append an action entry to the action log with a timestamp.

        Args:
            entry (dict): The action log entry to append.
        """
        #entry["timestamp"] = time.time()
        #self.blackboard.setdefault("actions_log", []).append(entry) Now for debuging
        self._save_to_file()

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
        self._save_to_file()

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
        self._save_to_file()

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
    
    def update_state(self, agent_name: str, new_state: dict):
        """
        Update the blackboard based on the agent name and the new state it provides.

        Args:
            agent_name (str): The name of the agent performing the update.
            new_state (dict): The new partial state information to merge.
        """
        if not isinstance(new_state, dict):
            raise ValueError("new_state must be a dictionary")

        # Example logic - call specific update methods based on agent type
        if agent_name.lower() == "reconagent":
            self._update_from_recon_agent(new_state)
        elif agent_name.lower() == "vulnagent":
            self._update_from_vuln_agent(new_state)
        elif agent_name.lower() == "exploitagent":
            self._update_from_exploit_agent(new_state)
        else:
            raise ValueError(f"Unknown agent name: '{agent_name}'")

        self._save_to_file()

    def _update_from_recon_agent(self, new_state: dict):
        """
        Smart merge of ReconAgent results into the blackboard.
        Only adds new information without deleting or overwriting existing data.
        """
       # self._smart_merge(self.blackboard, new_state)
        #self.blackboard = validate_state(self.blackboard)
        #self.blackboard = sort_state(self.blackboard)
        self.blackboard.clear()
        self.blackboard.update(new_state)
        self._save_to_file()

    def _smart_merge(self, base: dict, incoming: dict):
        """
        Recursively merges incoming into base.
        - Existing fields stay as-is.
        - Missing fields are added.
        - Lists are merged intelligently (without duplicates).
        - Nested dicts are merged recursively.
        """
        for key, value in incoming.items():
            if key not in base:
                base[key] = value
            else:
                if isinstance(base[key], dict) and isinstance(value, dict):
                    # Recursively merge dictionaries
                    self._smart_merge(base[key], value)
                elif isinstance(base[key], list) and isinstance(value, list):
                    # Merge lists without duplicates (assuming list of dicts or primitives)
                    existing = set(map(self._freeze, base[key]))
                    for item in value:
                        if self._freeze(item) not in existing:
                            base[key].append(item)
                else:
                    # If base already has a primitive value (str, int, etc), keep it, don't overwrite
                    pass

    def _freeze(self, item):
        """
        Converts dicts/lists into a hashable (tuple) structure for set membership checks.
        This is needed to detect duplicates in lists.
        """
        if isinstance(item, dict):
            return tuple(sorted((k, self._freeze(v)) for k, v in item.items()))
        if isinstance(item, list):
            return tuple(self._freeze(x) for x in item)
        return item

    def _update_from_vuln_agent(self, new_state: dict):
        """
        Update fields relevant to VulnAgent.
        """
        if "cpes" in new_state:
            self.blackboard["cpes"] = new_state["cpes"]
        if "vulnerabilities_found" in new_state:
            self.blackboard["vulnerabilities_found"] = new_state["vulnerabilities_found"]
        self._save_to_file()

    def _update_from_exploit_agent(self, new_state: dict):
        """
        Update fields relevant to VulnAgent. 
        """
        if "shell" in new_state:
            self.blackboard["shell"] = new_state["shell"]
        if "failed_CVEs" in new_state:
            self.blackboard["failed_CVEs"] = new_state["failed_CVEs"]
        self._save_to_file()

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
        self._save_to_file()
    
    def _save_to_file(self):
        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.blackboard, f, indent=2)
        except Exception as e:
            print(f"[!] Failed to save blackboard to {self.json_path}: {e}")