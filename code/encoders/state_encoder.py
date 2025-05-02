import hashlib
import json
import torch
import numbers
import numpy as np
import hashlib

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
        max_features: int = 1024
    ):
        """
        Args:
            action_space (list): List of all valid action strings.
            default_state (dict): A “blank” state dict containing every
                                  possible key (even empty), used to fix our feature order.
            max_features (int): Fixed length of the output state vector.
        """
        if default_state is None:
            default_state = initialize_blackboard()
            
        self.default_state = default_state 
        self.max_features = max_features
        self.action_space = action_space
        self.action_to_index = {a: i for i, a in enumerate(action_space)}
        self.encoded_to_state = {}

        # 1) flatten the provided default_state and sort its keys once
        flat_defaults = self._flatten_state(default_state)
        self.feature_keys = sorted(flat_defaults.keys())

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
        Uses self.feature_keys to guarantee a stable ordering of every feature.
        """
        # 1) flatten the current state
        flat = self._flatten_state(state)

        # 2) append action‐history counts
        actions_vector = np.zeros(len(self.action_space), dtype=np.float32)
        for a in actions_history:
            idx = self.action_to_index.get(a)
            if idx is not None:
                actions_vector[idx] += 1.0
        for i, cnt in enumerate(actions_vector):
            flat[f"action_history_idx_{i}"] = cnt

        # 3) build the normalized values in the fixed order
        encoded = []
        for key in self.feature_keys:
            raw = flat.get(key, 0.0)
            encoded.append(self._normalize_value(key, raw))

        # 4) pad or truncate
        if len(encoded) < self.max_features:
            encoded += [0.0] * (self.max_features - len(encoded))
        else:
            encoded = encoded[: self.max_features]

        # 5) to tensor
        vec = torch.tensor(encoded, dtype=torch.float32)

        # 6) store reverse mapping
        vk = self._vector_to_key(vec)
        if vk not in self.encoded_to_state:
            self.encoded_to_state[vk] = state

        print(f"[Encoder] Encoded vector of length {len(encoded)}")
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

        if prefix.endswith("vulnerabilities_found") or prefix.endswith("cpes"):
            return {}

        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                items.update(self._flatten_state(v, full_key))
        elif isinstance(obj, list):
            if prefix.endswith("failed_CVEs"):
                for i, cve in enumerate(obj[:5]):  # מגבילים ל־5 CVEs
                    if isinstance(cve, str) and cve.startswith("CVE-"):
                        digits = ''.join(filter(str.isdigit, cve))
                        if digits:
                            key = f"failed_cve_idx_{i}"
                            #print(f"[DEBUG] Found failed CVE {cve} → {digits} → {value} → saved as '{key}'")
                            items[key] = float(int(digits))  # נשלח לנרמול אח"כ
            else:
                for i, v in enumerate(obj):
                    full_key = f"{prefix}[{i}]"
                    items.update(self._flatten_state(v, full_key))
        elif isinstance(obj, bool):
            items[prefix] = 1.0 if obj else 0.0
        elif isinstance(obj, numbers.Number):
            items[prefix] = float(obj)
        elif isinstance(obj, str):
            # אם המחרוזת היא רק מספרים (למשל "445")
            if obj.isdigit():
                items[prefix] = float(obj)
            else:
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
            elif "failed_cve_idx" in key:
                norm = min(value / 99999999.0, 1.0)
                print(f"[DEBUG] Normalizing {key}: raw={value}, normalized={norm}")
                return norm
            elif any(field in key for field in ["service", "web_directories_status", "os"]):
                return min(value / 1e6, 1.0)
            else:
                return min(value / 1e6, 1.0)
        return 0.0

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
    encoder = StateEncoder(action_space=action_space, max_features=1024)

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
