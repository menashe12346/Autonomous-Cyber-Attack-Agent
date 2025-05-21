import hashlib
import json
import torch
import numbers
import numpy as np
import re
import sys
import os

from config import STATE_SCHEMA, MAX_ENCODING_FEATURES
from blackboard.blackboard import initialize_blackboard

class StateEncoder:
    """
    Encodes complex nested blackboard state structures into fixed-length numerical vectors
    suitable for use as input to neural networks.
    """

    def __init__(
        self,
        action_space: list,
        default_state: dict = None,
    ):
        """
        Args:
            action_space (list): List of all valid action strings.
            default_state (dict): A “blank” state dict containing every
                                  possible key (even empty), used to fix our feature order.
        """
        if default_state is None:
            default_state = initialize_blackboard()
            
        self.default_state = default_state 
        self.action_space = action_space
        self.action_to_index = {a: i for i, a in enumerate(action_space)}
        self.encoded_to_state = {}

        self.schema = STATE_SCHEMA
        self.schema_encoders = {
            k: v.get("encoder") for k, v in self.schema.items()
        }
        self.schema_types = {
            k: v.get("type") for k, v in self.schema.items()
        }

        # 1) flatten the provided default_state and sort its keys once
        flat_defaults = self._flatten_state(default_state)
        self.feature_keys = sorted(flat_defaults.keys())
        self.feature_keys += [f"action_history_idx_{i}" for i in range(len(self.action_space))] #DEBUG for now

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
    
    def count_encoder(self, count: float) -> float:
        return min(count / 100.0, 1.0)

    def normalize_by_specific_number(self, value: float, key: str) -> float:
        cfg = self.schema.get(key, {})
        norm = cfg.get("num_for_normalization", 1.0)
        return min(value / norm, 1.0)
    
    def _apply_encoder(self, key: str, raw):
        entry = self.schema.get(key, {})
        enc = entry.get("encoder")

        if enc == "base100_encode":

            return self.base100_encode(raw) if isinstance(raw, str) else float(raw)

        if enc == "count_encoder":
            return self.count_encoder(raw)

        if enc == "normalize_by_specific_number":
            return self.normalize_by_specific_number(raw, key)

        return self._normalize_value(key, raw)

    def encode(self, state: dict, actions_history: list) -> torch.Tensor:
        # 1) flatten
        flat = self._flatten_state(state)

        # 2) action history
        actions_vector = np.zeros(len(self.action_space), dtype=np.float32)
        for a in actions_history:
            idx = self.action_to_index.get(a)
            if idx is not None:
                actions_vector[idx] += 1.0
        for i, cnt in enumerate(actions_vector):
            flat[f"action_history_idx_{i}"] = cnt

        # 3) apply encoders according to schema
        encoded = []
        for key in self.feature_keys:
            raw = flat.get(key, 0.0)
            val = self._apply_encoder(key, raw)
            encoded.append(val)

        # 4) pad/truncate
        if len(encoded) < MAX_ENCODING_FEATURES:
            encoded += [0.0] * (MAX_ENCODING_FEATURES - len(encoded))
        else:
            encoded = encoded[: MAX_ENCODING_FEATURES]

        # 5)
        vec = torch.tensor(encoded, dtype=torch.float32)
        vk = self._vector_to_key(vec)
        if vk not in self.encoded_to_state:
            self.encoded_to_state[vk] = state

        #print(f"[Encoder] Encoded vector of length {len(encoded)}")
        return vec

    def decode(self, vector: torch.Tensor) -> dict:
        """
        Retrieves the original state dictionary corresponding to a previously encoded vector.

        Args:
            vector (torch.Tensor): The encoded vector.

        Returns:
            dict: The original blackboard state (if exists).
        """
        vector_key = self._vector_to_key(vector)
        return self.encoded_to_state.get(vector_key, {})
    
    def _vector_to_key(self, vector: torch.Tensor) -> str:
        """
        Generates a stable and unique key from a torch tensor
        by hashing its raw bytes. Ensures compatibility across CPU/GPU.

        Args:
            vector (torch.Tensor): Input tensor to hash.

        Returns:
            str: A unique hash key representing the tensor.
        """
        if vector.is_cuda:
            vector = vector.cpu()
        vector_bytes = vector.numpy().tobytes()
        return hashlib.md5(vector_bytes).hexdigest()

    def _schema_key(self, prefix: str) -> str:
        return re.sub(r'\[\d+\]', '[]', prefix)

    def _flatten_state(self, obj, prefix='') -> dict:
        items = {}

        if prefix.endswith("vulnerabilities_found") or prefix.endswith("cpes"):
            return {}

        schema_key = self._schema_key(prefix)
        schema_entry = self.schema.get(schema_key, {})

        if schema_entry.get("encoder") == "count_encoder" and isinstance(obj, dict):
            return { prefix: float(len(obj)) }

        if schema_entry.get("type") == "list" and isinstance(obj, list):

            corr = schema_entry.get("correction_func")
            if corr and hasattr(self, corr):
                obj = getattr(self, corr)(obj)

            sub_items = {}
            for i, v in enumerate(obj):
                full_key = f"{prefix}[{i}]" if prefix else f"[{i}]"
                sub_items.update(self._flatten_state(v, full_key))
            return sub_items

        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                items.update(self._flatten_state(v, full_key))

        elif isinstance(obj, list):

            if prefix.endswith("failed_CVEs"):
                for i, cve in enumerate(obj[:5]):
                    if isinstance(cve, str) and cve.startswith("CVE-"):
                        digits = ''.join(filter(str.isdigit, cve))
                        if digits:
                            items[f"failed_cve_idx_{i}"] = float(int(digits))
            else:
                for i, v in enumerate(obj):
                    full_key = f"{prefix}[{i}]"
                    items.update(self._flatten_state(v, full_key))

        elif isinstance(obj, bool):
            items[prefix] = 1.0 if obj else 0.0

        elif isinstance(obj, numbers.Number):
            items[prefix] = float(obj)

        elif isinstance(obj, str):
            if obj.isdigit():
                items[prefix] = float(obj)
            else:
                items[prefix] = self.base100_encode(obj)

        else:
            items[prefix] = 0.0

        return items

    def _normalize_value(self, key: str, value: float) -> float:
        encoder = self.schema_encoders.get(key)

        if encoder == "normalize_by_specific_number":
            norm_val = self.schema.get(key, {}).get("num_for_normalization", 1.0)
            return min(value / norm_val, 1.0)

        elif encoder == "base100_encode":
            return min(value / 1e6, 1.0)

        elif encoder == "count_encoder":
            # מונה – אפשר לנרמל לפי גבול עליון רך כמו 100
            return min(value / 100.0, 1.0)

        elif "action_history" in key:
            return float(value)

        elif "failed_cve_idx" in key:
            return min(value / 99999999.0, 1.0)

        return min(value / 1e6, 1.0)

# [DEBUG]
def main():
    # Define two different blackboard states
    state1 = {
        "target": {
            "ip": "",
            "os": "",
            "services": [
                {"port": "", "protocol": "", "service": ""},
                {"port": "445", "protocol": "tcp", "service": "smb"},
            ]
        },
        "web_directories_status": {
            "200": {"": ""},
            "404": {"": ""}
        },
        "actions_history": ["nmap 192.168.1.20", "gobuster 192.168.1.20"]
    }

    state2 = {
        "target": {
            "ip": "",
            "os": "",
            "services": [
                {"port": "", "protocol": "", "service": ""},
                {"port": "666", "protocol": "tcp", "service": "smb"},
            ]
        },
        "web_directories_status": {
            "200": {"": ""},
            "403": {"": ""}
        },
        "actions_history": ["nmap 192.168.1.20", "gobuster 192.168.1.20"]
    }

    # Define action space
    action_space = [
        "nmap 192.168.1.10",
        "gobuster 192.168.1.10",
        "nmap 192.168.1.20",
        "gobuster 192.168.1.20"
    ]
    #torch.set_printoptions(threshold=torch.inf)
    # Create StateEncoder instance
    encoder = StateEncoder(action_space=action_space)

    # Encode the states
    encoded_state1 = encoder.encode(state1, state1["actions_history"])
    encoded_state2 = encoder.encode(state2, state2["actions_history"])

    # Print the encoded vectors
    print("\n=== Encoded State 1 ===")
    print(encoded_state1)

    print("\n=== Encoded State 2 ===")
    print(encoded_state2)

    # Calculate and print the difference
    difference = (encoded_state2 - encoded_state1).abs()
    print("\n=== Difference (absolute) ===")
    print(difference)

    # Optional: Highlight only where differences are nonzero
    nonzero_indices = torch.nonzero(difference).squeeze().tolist()
    if isinstance(nonzero_indices, int):
        nonzero_indices = [nonzero_indices]

    print("\n=== Indices with Differences ===")
    print(nonzero_indices)

if __name__ == "__main__":
    main()
