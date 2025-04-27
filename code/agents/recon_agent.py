import json
import hashlib
from agents.base_agent import BaseAgent
from tools.action_space import get_commands_for_agent


class ReconAgent(BaseAgent):
    """
    A specialized agent for reconnaissance actions in the attack simulation.
    It selects and executes recon commands to gather service and network info.
    """

    def __init__(self, blackboard_api, policy_model, replay_buffer, state_encoder, action_encoder, command_cache, model):
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
            model=model
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

    def get_reward(self, prev_state, action, next_state) -> float:
        """
        Calculate the reward based on changes in knowledge or system state.

        Args:
            prev_state: Previous state vector.
            action (str): Action that was taken.
            next_state: Resulting state vector.

        Returns:
            float: The reward value for this transition.
        """
        reward = 0.0
        reasons = []

        def _services_to_set(services):
            return set(
                (s.get("port", ""), s.get("protocol", ""), s.get("service", ""))
                for s in services if isinstance(s, dict)
            )

        try:
            prev_key = str(prev_state.tolist())
            next_key = str(next_state.tolist())

            prev_dict = self.state_encoder.encoded_to_state.get(prev_key, {})
            next_dict = self.state_encoder.encoded_to_state.get(next_key, {})

            actions_history = prev_dict.get("actions_history", [])
            print(actions_history)

            # Repeated action penalty
            if action in actions_history:
                reward -= 0.5
                reasons.append("Repeated action -0.5")
            else:
                reward += 0.2
                reasons.append("New action +0.2")

            # New services discovered
            prev_services = _services_to_set(prev_dict.get("target", {}).get("services", []))
            next_services = _services_to_set(next_dict.get("target", {}).get("services", []))
            new_services = next_services - prev_services
            reward += 1.0 * len(new_services)
            if new_services:
                reasons.append(f"{len(new_services)} new services discovered +{1.0 * len(new_services):.1f}")

            # New ports discovered
            prev_ports = set(prev_dict.get("target", {}).get("open_ports", []))
            next_ports = set(next_dict.get("target", {}).get("open_ports", []))
            new_ports = next_ports - prev_ports
            reward += 0.5 * len(new_ports)
            if new_ports:
                reasons.append(f"{len(new_ports)} new open ports +{0.5 * len(new_ports):.1f}")

            # New shell opened
            prev_shell = prev_dict.get("runtime_behavior", {}).get("shell_opened", {})
            next_shell = next_dict.get("runtime_behavior", {}).get("shell_opened", {})

            if not prev_shell.get("shell_type") and next_shell.get("shell_type"):
                reward += 5.0
                reasons.append("New shell opened +5.0")

            # Privilege escalation
            levels = {"": 0, "user": 1, "root": 2}
            prev_level = prev_shell.get("shell_access_level", "")
            next_level = next_shell.get("shell_access_level", "")
            if levels.get(next_level, 0) > levels.get(prev_level, 0):
                reward += 3.0
                reasons.append(f"Privilege escalation from {prev_level} to {next_level} +3.0")

            # Useless repetition penalty
            if not new_services and not new_ports and not next_shell.get("shell_type"):
                if action in actions_history:
                    reward -= 1.0
                    reasons.append("No new discoveries and repeated action -1.0")

            # Debug summary
            print(f"[Reward Debug] Action: {action}")
            print(f"[Reward Debug] New services: {len(new_services)}")
            print(f"[Reward Debug] New ports: {len(new_ports)}")
            print(f"[Reward Debug] Shell opened: {next_shell.get('shell_type')}")
            print(f"[Reward Debug] Total reward: {reward:.4f}")

            print("\n[Reward Summary]")
            print(f"Action: {action}")
            print("Reasons:")
            for r in reasons:
                print(f" - {r}")
            print(f"Total reward: {reward:.4f}\n")

            return reward

        except Exception as e:
            print(f"[!] Reward computation failed: {e}")
            return 0.0