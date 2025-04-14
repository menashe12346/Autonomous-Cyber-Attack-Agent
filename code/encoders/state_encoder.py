import hashlib
import json
import torch
import numbers
import numpy as np

class StateEncoder:
    """
    Encodes complex nested blackboard state structures into fixed-length numerical vectors
    suitable for use as input to neural networks.
    """

    def __init__(self, action_space: list, max_features: int = 128):
        """
        Args:
            action_space (list): List of all valid action strings.
            max_features (int): Fixed length of the output state vector.
        """
        self.encoded_to_state = {}  # Maps stringified vectors to original state dicts
        self.max_features = max_features
        self.action_space = action_space
        self.action_to_index = {action: i for i, action in enumerate(action_space)}

    def base100_encode(self, text: str) -> float:
        """
        Encodes a string to a base-100 floating point number in [0, 1).

        Args:
            text (str): Input string (e.g., service name, OS, etc.)

        Returns:
            float: Encoded value between 0 and 1.
        """
        base = 100
        code = 0
        for i, c in enumerate(text[:5]):
            code += ord(c) * (base ** (4 - i))
        max_code = (base ** 5) - 1
        return code / max_code

    def encode(self, state: dict, actions_history: list) -> torch.Tensor:
        """
        Converts the blackboard state and action history into a fixed-length torch vector.

        Args:
            state (dict): The full blackboard state.
            actions_history (list): List of actions executed by the agent so far.

        Returns:
            torch.Tensor: A vector of shape (max_features,) representing the state.
        """
        # Flatten the state
        flat_state = self._flatten_state(state)

        # Encode action history as one-hot
        actions_vector = np.zeros(len(self.action_space), dtype=np.float32)
        for action in actions_history:
            if action in self.action_to_index:
                idx = self.action_to_index[action]
                actions_vector[idx] = 1.0

        # Add action history to the flat dictionary
        for i, val in enumerate(actions_vector):
            flat_state[f"action_history_idx_{i}"] = val

        # Sort keys to ensure consistent ordering
        sorted_items = sorted(flat_state.items())
        encoded_values = [self._normalize_value(k, v) for k, v in sorted_items]

        # Pad or truncate to fixed length
        if len(encoded_values) < self.max_features:
            encoded_values += [0.0] * (self.max_features - len(encoded_values))
        else:
            encoded_values = encoded_values[:self.max_features]

        # Convert to tensor
        vector = torch.tensor(encoded_values, dtype=torch.float32)

        # Store reverse mapping for debug and reward tracking
        vector_key = str(vector.tolist())
        self.encoded_to_state[vector_key] = state

        print(f"[Encoder] Encoded vector of length {len(encoded_values)} (state + history)")
        return vector

    def decode(self, vector_key: str) -> dict:
        """
        Retrieves the original state dictionary corresponding to a previously encoded vector.

        Args:
            vector_key (str): The stringified vector key.

        Returns:
            dict: The original blackboard state (if exists).
        """
        return self.encoded_to_state.get(vector_key, {})

    def _flatten_state(self, obj, prefix='') -> dict:
        """
        Flattens a nested dictionary or list into a single-level dict of key→value.

        Args:
            obj: The structure to flatten.
            prefix: Internal prefix used for recursion.

        Returns:
            dict: Flattened key-value pairs.
        """
        items = {}

        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                items.update(self._flatten_state(v, full_key))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                full_key = f"{prefix}[{i}]"
                items.update(self._flatten_state(v, full_key))
        elif isinstance(obj, bool):
            items[prefix] = 1.0 if obj else 0.0
        elif isinstance(obj, numbers.Number):
            items[prefix] = float(obj)
        elif isinstance(obj, str):
            items[prefix] = self.base100_encode(obj)
        else:
            items[prefix] = 0.0

        return items

    def _normalize_value(self, key: str, value: float) -> float:
        """
        Normalizes values based on the type of field they represent.

        Args:
            key (str): Feature name (used to detect type like "port", "service", etc.)
            value (float): The numeric value to normalize.

        Returns:
            float: Normalized value between 0 and 1.
        """
        if isinstance(value, (int, float)):
            if "port" in key:
                return min(value / 65535.0, 1.0)
            elif "protocol" in key:
                return min(value / 3.0, 1.0)
            elif "action_history" in key:
                return float(value)
            elif any(field in key for field in ["service", "web_directories_status", "os"]):
                return min(value / 1e6, 1.0)
            else:
                return min(value / 1e6, 1.0)
        return 0.0
