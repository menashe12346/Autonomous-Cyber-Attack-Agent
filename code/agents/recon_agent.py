import json
import hashlib
from collections import Counter


from agents.base_agent import BaseAgent
from tools.action_space import get_commands_for_agent
from utils.utils import get_nested, get_first_word
from config import STATE_SCHEMA

def traverse_schema_key(data, key_parts):
        """
        Recursively retrieves all values pointed to by the schema key parts.
        Supports nested dicts and lists (using '[]' to indicate lists).

        Args:
            data (dict or list): The current level of the data to examine.
            key_parts (list): List of key parts from a parsed schema key.

        Returns:
            list: All values reached by traversing the key parts.
        """
        if not key_parts:
            return [data]

        current = key_parts[0]
        rest = key_parts[1:]

        results = []

        if isinstance(data, dict):
            if current.endswith("[]"):
                list_key = current[:-2]
                sublist = data.get(list_key, [])
                if isinstance(sublist, list):
                    for item in sublist:
                        results.extend(traverse_schema_key(item, rest))
            else:
                next_data = data.get(current)
                if next_data is not None:
                    results.extend(traverse_schema_key(next_data, rest))

        elif isinstance(data, list):
            for item in data:
                results.extend(traverse_schema_key(item, key_parts))

        return results

class ReconAgent(BaseAgent):
    """
    A specialized agent for reconnaissance actions in the attack simulation.
    It selects and executes recon commands to gather service and network info.
    """

    def __init__(self, blackboard_api, policy_model, replay_buffer, state_encoder, action_encoder, command_cache, model, epsilon, os_linux_dataset, os_linux_kernel_dataset):
        """
        Initialize the ReconAgent with access to the blackboard and learning components.

        Args:
            blackboard_api (BlackboardAPI): Shared state interface.
            policy_model (PolicyModel): Q-network.
            replay_buffer: Experience replay buffer.
            state_encoder: State vector encoder.
            action_encoder: Action index encoder.
            command_cache: Shared cache of previously executed commands.
            model: LLM interface used for output parsing.
        """
        ip = blackboard_api.blackboard["target"]["ip"]
        super().__init__(
            name="ReconAgent",
            blackboard_api=blackboard_api,
            action_space=get_commands_for_agent("recon"),
            policy_model=policy_model,
            replay_buffer=replay_buffer,
            state_encoder=state_encoder,
            action_encoder=action_encoder,
            command_cache=command_cache,
            model=model,
            epsilon=epsilon,
            os_linux_dataset=os_linux_dataset,
            os_linux_kernel_dataset=os_linux_kernel_dataset
        )

    def should_run(self):
        """
        Determine whether the agent should run in the current blackboard state.

        Returns:
            bool: True if the agent should act, False otherwise.
        """
        bb = self.blackboard_api.blackboard
        target = bb.get("target", {})
        runtime = bb.get("runtime_behavior", {})
        actions_log = bb.get("actions_log", [])
        errors = bb.get("errors", [])
        impact = bb.get("attack_impact", {})

        services = target.get("services", [])
        open_ports = target.get("open_ports", [])

        # 1. No services or ports yet
        if not services and not open_ports:
            return True

        # 2. Too few results
        if len(services) < 2 and len(open_ports) < 2:
            return True

        # 3. Errors from this agent
        for err in errors:
            if err.get("agent") == self.name:
                return True

        # 4. Hasn't run recently
        last_time = None
        for log in reversed(actions_log):
            if log.get("agent") == self.name:
                last_time = log.get("timestamp")
                break
        if last_time is None:
            return True

        import time
        if time.time() - last_time > 300:
            return True

        # 5. Shell already open
        shell = runtime.get("shell_opened", {})
        if shell.get("shell_type") and shell.get("shell_access_level"):
            return False

        # 6. Detected by defenses
        if impact.get("detected_by_defenses", False):
            return False

        # ----- [DEBUG] ----- #
        #if prev_dict.get("os"):
        #    return False

        return True
    
    def get_reward(self, prev_dict: dict, action: str, next_dict: dict, output: str) -> float:
        """
        Generic reward calculation based solely on STATE_SCHEMA.
        - Rewards discovery of new primitive or dict-keys/list-items per schema key.
        - Penalizes repeated actions and no discoveries.
        """
        reward = 0.0
        reasons = []

        schema = self.state_encoder.schema

        # 1) Action repeat penalty / first-time bonus
        if action in self.actions_history:
            cnt = self.actions_history.count(action)
            pen = -2.0 * cnt
            reward += pen
            reasons.append(f"Action repeated {cnt} times {pen:+.1f}")
        else:
            reward += 0.1
            reasons.append("First time action +0.1")

        # helper to flatten any schema-extracted value v into primitives (strings)
        def flatten_value(v):
            if isinstance(v, dict):
                return [str(k).strip() for k in v.keys() if str(k).strip()]
            if isinstance(v, list):
                flat = []
                for x in v:
                    flat.extend(flatten_value(x))
                return flat
            return [str(v).strip()] if str(v).strip() else []

        # traverse and compare for each schema key
        for raw_key, meta in schema.items():
            weight = meta.get("reward", 0.0)
            if weight <= 0:
                continue

            # parse key parts for list recursion
            parts = []
            for part in raw_key.split("."):
                if part.endswith("[]"):
                    parts.append(part[:-2] + "[]")
                else:
                    parts.append(part)

            prev_vals = traverse_schema_key(prev_dict, parts)
            next_vals = traverse_schema_key(next_dict, parts)

            # flatten all values/dict-keys/list-items to primitive strings
            prev_set = set()
            for v in prev_vals:
                prev_set.update(flatten_value(v))

            next_set = set()
            for v in next_vals:
                next_set.update(flatten_value(v))

            new_items = next_set - prev_set
            if new_items:
                total = weight * len(new_items)
                reward += total
                reasons.append(
                    f"Discovered {len(new_items)} new values for {raw_key} +{total:.2f}"
                )

        # 3) Fallback penalty if nothing found beyond the action step
        if len(reasons) == 1:
            reward -= 1.0
            reasons.append("No new fields discovered -1.0")

        # Debug output
        print("\n[Reward Debug]")
        print(f"Action: {action}")
        for r in reasons:
            print("  ", r)
        print(f"Total raw reward: {reward:.2f}\n")

        # 4) Update history
        self.prev_state = dict(next_dict)

        return reward/4
