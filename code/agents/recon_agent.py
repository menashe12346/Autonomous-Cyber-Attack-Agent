from agents.base_agent import BaseAgent
from tools.action_space import get_commands_for_agent
import hashlib
import json

class ReconAgent(BaseAgent):
    def __init__(self, blackboard_api, policy_model, replay_buffer, state_encoder, action_encoder, command_cache, model):
        ip = blackboard_api.blackboard["target"]["ip"]  # שליפת IP מהמטרה
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
        מחליט אם הסוכן צריך לפעול לפי כלל המידע שב־Blackboard,
        כולל שירותים, פורטים, שגיאות, shell פתוח, זיהוי ע״י הגנות ועוד.
        """
        bb = self.blackboard_api.blackboard
        target = bb.get("target", {})
        runtime = bb.get("runtime_behavior", {})
        actions_log = bb.get("actions_log", [])
        errors = bb.get("errors", [])
        impact = bb.get("attack_impact", {})

        services = target.get("services", [])
        open_ports = target.get("open_ports", [])

        # 1. אין שירותים ואין פורטים כלל => חובה להריץ
        if not services and not open_ports:
            return True

        # 2. אם יש פחות מ־2 שירותים ופורטים => כנראה הסריקה חלקית
        if len(services) < 2 and len(open_ports) < 2:
            return True

        # 3. אם הייתה שגיאה בסריקה קודמת מהסוכן הזה
        for err in errors:
            if err.get("agent") == self.name:
                return True

        # 4. אם עברו יותר מ־5 דקות מאז הפעם האחרונה שהסוכן פעל
        last_time = None
        for log in reversed(actions_log):
            if log.get("agent") == self.name:
                last_time = log.get("timestamp")
                break
        if last_time is None:
            return True  # הסוכן טרם פעל

        import time
        if time.time() - last_time > 300:
            return True

        # 5. אם כבר יש shell פתוח ⇒ אולי מיותר לסרוק
        shell = runtime.get("shell_opened", {})
        if shell.get("shell_type") and shell.get("shell_access_level"):
            return False

        # 6. אם הסוכן נחשף – אולי לא נרצה לסרוק שוב כרגע
        if impact.get("detected_by_defenses", False):
            return False

        # אם כלום מאלה לא קרה – לא צריך להריץ
        #return False
        return True # for debug

    def get_reward(self, prev_state, action, next_state) -> float:
        """
        מחשב תגמול לפי:
        - שינוי במידע (שירותים, פורטים, shell)
        - שימוש חוזר או חדשני בפעולה
        - יעילות הפעולה
        """
        reward = 0.0

        try:
            # חילוץ ה-state המלאים מהאובייקט המקודד
            prev_hash = hashlib.sha256(json.dumps(prev_state.tolist(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            next_hash = hashlib.sha256(json.dumps(next_state.tolist(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()

            prev_dict = self.state_encoder.encoded_to_state.get(prev_hash, {})
            next_dict = self.state_encoder.encoded_to_state.get(next_hash, {})

            # היסטוריית פקודות
            actions_history = prev_dict.get("actions_history", [])

            # בדיקה אם הפקודה כבר בוצעה
            if action in actions_history:
                reward -= 0.5  # ענישה קלה על חזרתיות
            else:
                reward += 0.2  # בונוס קל על חקירה

            # בדיקת שיפור במידע (services, ports)
            prev_services = set(prev_dict.get("target", {}).get("services", []))
            next_services = set(next_dict.get("target", {}).get("services", []))
            new_services = next_services - prev_services
            reward += 1.0 * len(new_services)

            prev_ports = set(prev_dict.get("target", {}).get("open_ports", []))
            next_ports = set(next_dict.get("target", {}).get("open_ports", []))
            new_ports = next_ports - prev_ports
            reward += 0.5 * len(new_ports)

            # תגמול אם shell חדש נפתח
            prev_shell = prev_dict.get("runtime_behavior", {}).get("shell_opened", {})
            next_shell = next_dict.get("runtime_behavior", {}).get("shell_opened", {})

            if not prev_shell.get("shell_type") and next_shell.get("shell_type"):
                reward += 5.0

            # תגמול נוסף לפי שדרוג רמת גישה
            levels = {"": 0, "user": 1, "root": 2}
            prev_level = prev_shell.get("shell_access_level", "")
            next_level = next_shell.get("shell_access_level", "")
            if levels.get(next_level, 0) > levels.get(prev_level, 0):
                reward += 3.0

            # אם לא נוספו שירותים, פורטים או shell חדש – והפקודה בוצעה בעבר ⇒ נעניש קלות
            if not new_services and not new_ports and not next_shell.get("shell_type"):
                if action in actions_history:
                    reward -= 1.0  # ענישה על בזבוז פעולה

            return reward

        except Exception as e:
            print(f"[!] Reward computation failed: {e}")
            return 0.0