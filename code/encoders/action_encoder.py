from typing import List

class ActionEncoder:
    """
    Encodes and decodes actions using consistent index-based mappings.
    Converts between string-based actions and their numeric representation.
    """

    def __init__(self, actions: List[str]):
        """
        Args:
            actions (List[str]): List of possible action strings.
        """
        self.action_to_index = {action: i for i, action in enumerate(actions)}
        self.index_to_action = {i: action for i, action in enumerate(actions)}

    def encode(self, action: str) -> int:
        """
        Converts an action string to its corresponding index.

        Args:
            action (str): Action command (e.g., "nmap -sV {ip}")

        Returns:
            int: Index of the action in the action space.

        Raises:
            KeyError: If the action is not in the known action space.
        """
        if action not in self.action_to_index:
            raise KeyError(f"Action '{action}' not found in action space.")
        return self.action_to_index[action]

    def decode(self, index: int) -> str:
        """
        Converts an action index back to its corresponding command string.

        Args:
            index (int): Index in the action space.

        Returns:
            str: Action command string.

        Raises:
            KeyError: If the index is out of bounds.
        """
        if index not in self.index_to_action:
            raise KeyError(f"Index {index} is not valid in action space.")
        return self.index_to_action[index]
