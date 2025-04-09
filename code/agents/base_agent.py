from abc import ABC, abstractmethod
import random
import subprocess
from models.prompts import PROMPT_1, PROMPT_2, clean_output_prompt
import json
from utils.utils import remove_comments_and_empty_lines, extract_final_json

class BaseAgent(ABC):
    def __init__(self, name, action_space, blackboard_api, replay_buffer, policy_model, state_encoder, action_encoder, command_cache, model, epsilon=0.1):
        self.name = name
        self.action_space = action_space
        self.blackboard_api = blackboard_api
        self.replay_buffer = replay_buffer
        self.policy_model = policy_model
        self.state_encoder = state_encoder
        self.action_encoder = action_encoder
        self.last_state = None
        self.last_action = None
        self.epsilon = epsilon
        self.actions_history = [] 
        self.command_cache = command_cache  # פקודות שהורצו והתוצאה נשמרה
        self.model = model

    @abstractmethod
    def should_run(self) -> bool:
        """
        בודקת אם הסוכן צריך לפעול כעת לפי מצב המערכת, ניסיונות קודמים, והגדרות.
        """
        pass

    def run(self):
        """
        הלולאה הראשית של הסוכן – מייצגת ניסיון פעולה ולמידה אחת.
        """
        raw_state = self.get_state_raw()  # שליפת מצב גולמי
        raw_state_with_history = dict(raw_state)
        raw_state_with_history["actions_history"] = self.actions_history.copy()
        state = self.state_encoder.encode(raw_state_with_history, self.actions_history)
        self.last_state = state

        action = self.choose_action(state)
        self.last_action = action

        self.actions_history.append(action)  # הוספת פעולה להיסטוריה

        print(f"\n[+] Agent: {self.name}")
        print(f"    Current state: {str(state)[:8]}...")  # מקצר את ההדפסה
        print(f"    Chosen action: {action}")

        result = remove_comments_and_empty_lines(self.perform_action(action))
        print("\033[1;32m" + str(result) + "\033[0m")

        # רק אם הפלט כולל יותר מ־300 מילים – לבצע ניקוי
        if len(result.split()) > 200:
            try:
                cleaned_output = self.clean_output(clean_output_prompt(result))
            except Exception as e:
                print(f"[!] Failed to clean output: {e}")
                cleaned_output = result
        else:
            cleaned_output = result
        print(f"\033[94mcleaned_output - {cleaned_output}\033[0m")

        parsed_info_raw = self.parse_output(cleaned_output)
        parsed_info = extract_final_json(parsed_info_raw)
        print(f"parsed_info - {parsed_info}")
        # חילוץ מחרוזת ה-JSON מתוך הרשימה
        parsed_json_str = next((p for p in parsed_info if p.strip().startswith("{")), None)

        if parsed_json_str:
            try:
                parsed_json = json.loads(parsed_json_str)
                self.blackboard_api.overwrite_blackboard(parsed_json)
            except json.JSONDecodeError as e:
                print(f"[!] Failed to decode JSON from model output: {e}")
        else:
            print("[!] No valid JSON found in parsed_info")

        raw_next_state = self.get_state_raw()
        raw_next_state_with_history = dict(raw_next_state)
        raw_next_state_with_history["actions_history"] = self.actions_history.copy()
        next_state = self.state_encoder.encode(raw_next_state_with_history, self.actions_history)
        reward = self.get_reward(state, action, next_state)

        # בניית קלט למודל לצורך עדכון ולוג
        experience = {
            "state": state,
            "action": self.action_space.index(action),
            "reward": reward,
            "next_state": next_state
        }

        # עדכון מודל וחישוב q_pred + loss
        q_pred, loss = self.policy_model.update(experience)

        print(f"    Predicted Q-value: {q_pred:.4f}")
        print(f"    Actual reward:     {reward:.4f}")
        print(f"    Loss:              {loss:.6f}")

        # הוספת חוויה למאגר
        self.replay_buffer.add_experience(state, self.action_space.index(action), reward, next_state, False)

        self.blackboard_api.append_action_log({
            "agent": self.name,
            "action": action,
            "result": result,
        })


    def get_state_raw(self):
        """
        מחלץ את מצב ה־blackboard_api כפי שהוא, לצורך קידוד עם היסטוריה.
        """
        return self.blackboard_api.get_state_for_agent(self.name)

    def get_state(self):
        """
        מחלץ את מצב ה-blackboard_api ומקודד אותו לוקטור קלט למודל.
        """
        return self.state_encoder.encode(self.get_state_raw(), self.actions_history)

    def choose_action(self, state_vector):
        """
        בוחרת פעולה לפי אסטרטגיית ε-greedy:
        - בהסתברות ε: פעולה אקראית (exploration)
        - בהסתברות 1-ε: הפעולה הכי טובה לפי policy_model (exploitation)
        """
        if random.random() < self.epsilon:
            # פעולה אקראית (חקירה)
            action_index = random.randint(0, len(self.action_space) - 1)
            self.decay_epsilon()
        else:
            # הפעולה הכי טובה לפי המודל
            action_index = self.policy_model.predict_best_action(state_vector)

        return self.action_space[action_index]
    
    def decay_epsilon(self, decay_rate=0.995, min_epsilon=0.01):
        self.epsilon = max(self.epsilon * decay_rate, min_epsilon)

    def perform_action(self, action: str) -> str:
        """
        ברירת מחדל להפעלת פעולה ע"י פקודת טרמינל על כתובת IP של הקורבן.
        מיועד לסוכנים שמשתמשים בפקודות מבוססות IP.
        """

        ip = self.blackboard_api.blackboard.get("target", {}).get("ip", "127.0.0.1")
        command = action.format(ip=ip)

        if action in self.command_cache:
            print(f"[Cache] Returning cached result for action: {action}")
            return self.command_cache[action]

        try:
            output = subprocess.check_output(command.split(), timeout=10).decode()
        except Exception as e:
            self.blackboard_api.add_error(self.name, action, str(e))
            output = ""

        self.command_cache[action] = output

        return output

    def parse_output(self, command_output: str) -> dict:
        """
        מפעיל את מודול הפענוח ומחזיר תובנות לתוך blackboard_api.
        """

        return self.model.run_prompts([PROMPT_1, PROMPT_2(command_output)])

    def clean_output(self, command_output: str) -> dict:
        return self.model.run_prompt(clean_output_prompt(command_output))


    @abstractmethod
    def get_reward(self, prev_state, action, next_state) -> float:
        """
        מחשב את ערך התגמול שהפעולה השיגה, לפי השינוי במצב.
        """
        # (יישום חיצוני – reward_calculator)
        raise NotImplementedError

    def update_policy(self, state, action, reward, next_state):
        """
        שולח את הנתונים ל-Replay Buffer והמודל מתעדכן בהתאם.
        """
        self.policy_model.update({
            "state": state,
            "action": self.action_space.index(action),
            "reward": reward,
            "next_state": next_state
        })
