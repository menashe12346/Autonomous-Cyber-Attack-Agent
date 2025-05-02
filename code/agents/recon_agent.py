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
        מחשבת תגמול חכם לפי:
            1) חזרה על פעולה
            2) גילוי שירותים חדשים
            3) גילוי תיקיות חדשות
            4) גילוי שדות OS חדשים
            5) עונש אם אין שום גילוי
        """
        reward = 0.0
        reasons = []

        # 1) היסטוריית אקשנים
        history = self.actions_history.copy()
        if action in history:
            count = history.count(action)
            penalty = -0.5 * count
            reward += penalty
            reasons.append(f"Action repeated {count} times {penalty:+.1f}")
        else:
            reward += 0.1
            reasons.append("First time action +0.1")

        # 2) שירותים חדשים
        def to_set(svcs):
            return set(
                (s.get("port",""), s.get("protocol",""), s.get("service",""))
                for s in svcs if isinstance(s, dict)
            )
        prev_sv = to_set(prev_dict.get("target",{}).get("services",[]))
        next_sv = to_set(next_dict.get("target",{}).get("services",[]))
        new_sv = next_sv - prev_sv
        if new_sv:
            bonus = 0.2 * len(new_sv)
            reward += bonus
            reasons.append(f"{len(new_sv)} new services +{bonus:.1f}")

        # 3) תיקיות web חדשות
        prev_dirs = {
            p for st in prev_dict.get("web_directories_status",{}).values()
            for p in st.keys() if p.strip()
        }
        next_dirs = {
            p for st in next_dict.get("web_directories_status",{}).values()
            for p in st.keys() if p.strip()
        }
        new_dirs = next_dirs - prev_dirs
        if new_dirs:
            bonus = 0.1 * len(new_dirs)
            reward += bonus
            reasons.append(f"{len(new_dirs)} new dirs +{bonus:.1f}")

        # 4) גילוי שדות OS
        prev_os = prev_dict.get("target",{}).get("os",{})
        next_os = next_dict.get("target",{}).get("os",{})

        def check_os(field, weight, desc):
            pv = prev_os.get(field,"") or ""
            nv = next_os.get(field,"") or ""
            if not pv.strip() and nv.strip():
                return (weight, f"Discovered {desc} '{nv}' +{weight:.2f}")
            return (0.0, None)

        for fld, w, d in [
            ("name",           0.2, "OS name"),
            ("kernel",         0.25,"kernel version"),
        ]:
            wv, msg = check_os(fld, w, d)
            if wv:
                reward += wv
                reasons.append(msg)

        # name under distribution
        pd = prev_os.get("distribution",{}) 
        nd = next_os.get("distribution",{})
        for fld, w, d in [
            ("name",    0.15,"distro name"),
            ("version", 0.15,"distro version"),
            ("architecture",   0.25,"architecture"),
        ]:
            pv = pd.get(fld,"") or ""
            nv = nd.get(fld,"") or ""
            if not pv.strip() and nv.strip():
                reward += w
                reasons.append(f"Discovered {d} '{nv}' +{w:.2f}")

        # 5) עונש אם לא גילו כלום
        if not new_sv and not new_dirs and all("Discovered" not in r for r in reasons):
            reward -= 1.0
            reasons.append("No new discoveries -1.0")

        # Debug
        print("\n[Reward Debug]")
        print(f"Action: {action}")
        for r in reasons:
            print("  ", r)
        print(f"Total raw reward: {reward:.2f}\n")

        reward = reward/4 # so it would be easier for the model to learn

        # אפשר לסקל או לחלק אם צריך, כרגע מחזירים כפי שמחושב
        return reward
