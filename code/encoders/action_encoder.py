# action_encoder.py

from typing import List

class ActionEncoder:
    def __init__(self, actions: List[str]):
        self.action_to_index = {action: i for i, action in enumerate(actions)}
        self.index_to_action = {i: action for i, action in enumerate(actions)}

    def encode(self, action: str) -> int:
        """
        מקבל מחרוזת של פקודה ומחזיר את האינדקס שלה.
        """
        return self.action_to_index[action]

    def decode(self, index: int) -> str:
        """
        מקבל אינדקס ומחזיר את הפקודה המתאימה.
        """
        return self.index_to_action[index]
