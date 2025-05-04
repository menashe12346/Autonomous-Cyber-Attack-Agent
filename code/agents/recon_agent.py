import json
import hashlib
from agents.base_agent import BaseAgent
from tools.action_space import get_commands_for_agent
from collections import Counter
from config import STATE_SCHEMA
from utils.utils import get_nested

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
            action_space=get_commands_for_agent("recon", ip),
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

        # ----- DEBUG ----- #
        if prev_dict.get("os"):
            return False

        return True
    def get_reward(self, prev_dict: dict, action: str, next_dict: dict) -> float:
        """
        מחשבת תגמול כללי לפי STATE_SCHEMA:
        - תגמול עבור גילוי שדות חדשים בהתאם ל-reward שב-schema
        - עונש על חזרה על פעולה
        - עונש אם לא התגלה כלום
        """
        reward = 0.0
        reasons = []

        # 1) חזרה על פעולה / פעולה ראשונה
        if action in self.actions_history:
            count = self.actions_history.count(action)
            penalty = -0.5 * count
            reward += penalty
            reasons.append(f"Action repeated {count} times {penalty:+.1f}")
        else:
            reward += 0.1
            reasons.append("First time action +0.1")

        schema = self.state_encoder.schema

        # 2) מעבר על כל שדה בסכמה
        for raw_key, info in schema.items():
            weight = info.get("reward", 0)
            if weight <= 0:
                continue

            enc = info.get("encoder", "")

            # A) count_encoder: ספירת פריטים בהבדל בין prev ל-next
            if enc == "count_encoder":
                prev_container = get_nested(prev_dict, raw_key) or {}
                next_container = get_nested(next_dict, raw_key) or {}
                try:
                    prev_count = len(prev_container)
                    next_count = len(next_container)
                except Exception:
                    continue
                diff = next_count - prev_count
                if diff > 0:
                    total = weight * diff
                    reward += total
                    reasons.append(
                        f"Discovered {diff} new items under {raw_key} +{total:.2f}"
                    )
                continue

            # B) list-element fields: raw_key contains "[]"
            if "[]" in raw_key:
                prefix, field = raw_key.split("[].")
                prev_list = get_nested(prev_dict, prefix) or []
                next_list = get_nested(next_dict, prefix) or []
                prev_vals = {
                    str(item.get(field, "")).strip()
                    for item in prev_list
                    if isinstance(item, dict)
                }
                next_vals = {
                    str(item.get(field, "")).strip()
                    for item in next_list
                    if isinstance(item, dict)
                }
                new_vals = next_vals - prev_vals
                if new_vals:
                    total = weight * len(new_vals)
                    reward += total
                    reasons.append(
                        f"Discovered {len(new_vals)} new '{field}' under {prefix} +{total:.2f}"
                    )
                continue

            # C) שדות רגילים (string / number)
            prev_val = str(get_nested(prev_dict, raw_key) or "").strip()
            next_val = str(get_nested(next_dict, raw_key) or "").strip()
            if not prev_val and next_val:
                reward += weight
                reasons.append(f"Discovered {raw_key} = '{next_val}' +{weight:.2f}")

        # 3) עונש אם לא התגלה כלום (מלבד repeat/first-time)
        if len(reasons) == 1:
            reward -= 1.0
            reasons.append("No new fields discovered -1.0")

        # Debug
        print("\n[Reward Debug]")
        print(f"Action: {action}")
        for r in reasons:
            print("  ", r)
        print(f"Total raw reward: {reward:.2f}\n")

        # 4) עדכון היסטוריה
        self.prev_state = dict(next_dict)

        return reward
