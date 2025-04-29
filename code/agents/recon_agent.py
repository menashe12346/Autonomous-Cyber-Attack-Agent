import json
import hashlib
from agents.base_agent import BaseAgent
from tools.action_space import get_commands_for_agent
from collections import Counter

class ReconAgent(BaseAgent):
    """
    A specialized agent for reconnaissance actions in the attack simulation.
    It selects and executes recon commands to gather service and network info.
    """

    def __init__(self, blackboard_api, policy_model, replay_buffer, state_encoder, action_encoder, command_cache, model, epsilon):
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
            epsilon=epsilon
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
        Calculates a smarter reward based on discoveries in services, web directories, and OS.

        Args:
            prev_dict (dict): Previous state dictionary.
            action (str): Action that was taken.
            next_dict (dict): Resulting state dictionary.

        Returns:
            float: The reward value for this transition.
        """
        reward = 0.0
        reasons = []

        def _services_to_ports_services(services):
            return set(
                (s.get("port", ""), s.get("protocol", ""), s.get("service", ""))
                for s in services if isinstance(s, dict)
            )

        try:
            # (1) היסטוריית אקשנים
            actions_history = self.actions_history.copy()

            # (2) ענישה/תגמול על חזרה
            if action in actions_history:
                count = actions_history.count(action)
                penalty = -0.5 * count
                reward += penalty
                reasons.append(f"Action repeated {count} times {penalty}")
            else:
                reward += 0.1
                reasons.append("First time action +0.1")

            # (3) גילוי שירותים חדשים
            prev_services = _services_to_ports_services(prev_dict.get("target", {}).get("services", []))
            next_services = _services_to_ports_services(next_dict.get("target", {}).get("services", []))
            new_services = next_services - prev_services

            print(f"[Reward Debug] prev_services: {prev_services}")
            print(f"[Reward Debug] next_services: {next_services}")
            print(f"[Reward Debug] new_services: {new_services}")

            reward += 0.2 * len(new_services)
            if new_services:
                reasons.append(f"{len(new_services)} new services discovered +{0.2 * len(new_services):.1f}")

            # (4) גילוי web directories חדשים
            prev_dirs = set()
            next_dirs = set()

            for status_code in prev_dict.get("web_directories_status", {}):
                prev_dirs.update(
                    path for path in prev_dict["web_directories_status"].get(status_code, {}).keys()
                    if path.strip()
                )

            for status_code in next_dict.get("web_directories_status", {}):
                next_dirs.update(
                    path for path in next_dict["web_directories_status"].get(status_code, {}).keys()
                    if path.strip()
                )

            new_dirs = next_dirs - prev_dirs

            print(f"[Reward Debug] prev_dirs: {prev_dirs}")
            print(f"[Reward Debug] next_dirs: {next_dirs}")
            print(f"[Reward Debug] new_dirs: {new_dirs}")

            reward += 0.1 * len(new_dirs)
            if new_dirs:
                reasons.append(f"{len(new_dirs)} new web directories discovered +{0.1 * len(new_dirs):.1f}")

            # (5) גילוי OS חדש
            prev_os = (prev_dict.get("target", {}).get("os") or "").strip().lower()
            next_os = (next_dict.get("target", {}).get("os") or "").strip().lower()

            if not prev_os and next_os:
                reward += 0.5
                reasons.append(f"New OS discovered: '{next_os}' +0.5")

            # (6) ענישה אם לא היה שום גילוי בכלל
            if not new_services and not new_dirs and not (not prev_os and next_os):
                reward -= 1.0
                reasons.append("No new discoveries -1.0")

            # Debug summary
            print(f"\n[Reward Debug]")
            print(f"Action: {action}")
            for r in reasons:
                print(f" - {r}")
            print(f"Total reward: {reward:.4f}\n")

            return reward/4

        except Exception as e:
            print(f"[!] Reward computation failed: {e}")
            return 0.0
