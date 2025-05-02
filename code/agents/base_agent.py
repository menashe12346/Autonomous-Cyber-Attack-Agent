import random
import subprocess
import json
import torch
from abc import ABC, abstractmethod
import numpy as np

from Cache.llm_cache import LLMCache
from Cache.commandLLM_cache import CommandLLMCache

from utils.prompts import PROMPT_1, PROMPT_2, clean_output_prompt, PROMPT_FOR_A_PROMPT
from utils.utils import remove_comments_and_empty_lines
from utils.state_check.state_validator import validate_state
from utils.state_check.state_correctness import correct_state
from utils.state_check.state_sorting import sort_state
from utils.json_fixer import fix_json

def remove_untrained_categories(state: dict, trained_categories: dict):
    # מחיקת קטגוריות ראשיות לא מאומנות
    keys_to_remove = [key for key in state if key not in trained_categories]
    for key in keys_to_remove:
        state.pop(key, None)

    # סינון שדות פנימיים בתוך קטגוריות
    for key, allowed_fields in trained_categories.items():
        if allowed_fields is None:
            continue  # שמור הכל בקטגוריה זו
        if key in state and isinstance(state[key], dict):
            inner_keys_to_remove = [inner_key for inner_key in state[key] if inner_key not in allowed_fields]
            for inner_key in inner_keys_to_remove:
                state[key].pop(inner_key, None)

class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the attack environment.
    Provides the main learning and acting loop, caching, output parsing, and interaction with the blackboard.
    """

    def __init__(self, name, action_space, blackboard_api, replay_buffer,
                 policy_model, state_encoder, action_encoder, command_cache, model, epsilon, os_linux_dataset, os_linux_kernel_dataset, min_epsilon = 0.01, epsilon_decay = 0.995):
        self.name = name
        self.action_space = action_space
        self.blackboard_api = blackboard_api
        self.replay_buffer = replay_buffer
        self.policy_model = policy_model
        self.state_encoder = state_encoder
        self.action_encoder = action_encoder
        self.command_cache = command_cache
        self.model = model
        self.epsilon = epsilon
        self.min_epsilon = min_epsilon
        self.epsilon_decay = epsilon_decay
        self.actions_history = []
        self.last_state = None
        self.encoded_last_state = None
        self.last_action = None
        self.llm_cache = LLMCache()
        self.command_llm_cache = CommandLLMCache()
        self.episode_total_reward = 0.0
        self.os_linux_dataset=os_linux_dataset,
        self.os_linux_kernel_dataset=os_linux_kernel_dataset

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # <-- חדש
 
    @abstractmethod
    def should_run(self) -> bool:
        """
        Must be implemented by subclasses to decide whether the agent should act now.
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_reward(self, prev_state, action, next_state) -> float:
        """
        Must be implemented by subclasses to compute the reward signal.
        """
        raise NotImplementedError

    def run(self):
        """
        Main loop of the agent: observe, choose action, perform, parse, learn, update.
        """
        #step 1: fill state withh all categories
        self.blackboard_api.fill_state(
            actions_history=self.actions_history.copy(),
            )
        # Step 1: get state
        state = dict(self.get_state_raw())
        encoded_state = self.state_encoder.encode(state, self.actions_history)
        self.last_state = state
        self.encoded_last_state = encoded_state
        print(f"encoded_state: {encoded_state}")

        # [DEBUG]
        print(f"last state: {json.dumps(state, indent=2)}")

        # Step 2: select action
        action = self.choose_action(encoded_state)
        self.last_action = action

        print(f"\n[+] Agent: {self.name}")
        print(f"    Current state: {str(state)[:8]}...")
        print(f"    Chosen action: {action}")

        # Step 3: execute action
        result = remove_comments_and_empty_lines(self.perform_action(action)) # TO DO: Improving remove_comments_and_empty_lines
        print("\033[1;32m" + str(result) + "\033[0m")

        # Step 4: clean output (if long)
        if len(result.split()) > 300:
            try:
                cleaned_output = self.clean_output(clean_output_prompt(result))
            except Exception as e:
                print(f"[!] Failed to clean output: {e}")
                cleaned_output = result
        else:
            cleaned_output = result
        print(f"\033[94mcleaned_output - {cleaned_output}\033[0m")

        # Step 5: parse, validate and update blackboard
        parsed_info = self.parse_output(cleaned_output)
        #print(f"parsed_info - {parsed_info}")

        self.blackboard_api.update_state(self.name, parsed_info)

        # Step 6: observe next state
        next_state = dict(self.get_state_raw())
        encoded_next_state = self.state_encoder.encode(next_state, self.actions_history)

        # Step 7: reward and update model
        reward = self.get_reward(state, action, next_state)
        self.episode_total_reward += reward
        #print(f"new state: {json.dumps(dict(self.state_encoder.decode(encoded_next_state)), indent=2)}")

        self.actions_history.append(action)

        experience = {
            "state": encoded_state,
            "action": self.action_space.index(action),
            "reward": reward,
            "next_state": encoded_next_state
        }

        q_pred, loss = self.policy_model.update(experience)

        print(f"    Predicted Q-value: {q_pred:.4f}")
        print(f"    Actual reward:     {reward:.4f}")
        print(f"    Loss:              {loss:.6f}")

        # Step 8: save experience
        self.replay_buffer.add_experience(encoded_state, self.action_space.index(action), reward, encoded_next_state, False)

        # Step 9: log action
        self.blackboard_api.append_action_log({
            "agent": self.name,
            "action": action,
            "result": result,
        })

    def choose_action(self, state_vector):
        """
        ε-greedy policy: choose random action with probability ε, else best predicted action.
        Also prints all predicted Q-values for analysis.
        """
        # הפוך את state_vector ל־Tensor אם צריך
        if not isinstance(state_vector, torch.Tensor):
            state_tensor = torch.tensor(state_vector, dtype=torch.float32).unsqueeze(0)
        else:
            state_tensor = state_vector.unsqueeze(0) if state_vector.ndim == 1 else state_vector

        state_tensor = state_tensor.to(next(self.policy_model.parameters()).device)

        # חיזוי Q-values
        with torch.no_grad():
            q_values = self.policy_model.forward(state_tensor).cpu().numpy().flatten()

        # הדפסה של כל הערכים
        print("\n[✓] Q-value predictions:")
        for action, q in zip(self.action_space, q_values):
            print(f"  {action:70s} => Q = {q:.4f}")

        # בחירת פעולה
        rnd = random.random() 
        if rnd < self.epsilon:
            print(f"\033[91m[! EXPLORATION] rnd={rnd:.4f} < ε={self.epsilon:.4f} → Choosing random action\033[0m")
            action_index = random.randint(0, len(self.action_space) - 1)
        else:
            action_index = int(np.argmax(q_values))

        return self.action_space[action_index]

    def decay_epsilon(self):
        """
        Gradually reduce exploration probability.
        """
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.min_epsilon)

    def get_state_raw(self):
        """
        Get the current blackboard state as-is (used for encoding).
        """
        return self.blackboard_api.get_state_for_agent(self.name)

    def get_state(self):
        """
        Encoded state vector.
        """
        return self.state_encoder.encode(self.get_state_raw(), self.actions_history)

    def perform_action(self, action: str) -> str:
        """
        Default behavior: run an IP-based shell command with the action template.
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
        
    def parse_output(self, command_output: str, retries: int = 3) -> dict:
        """
        Parse command output using the LLM. Use cache if available.
        Retry recursively if the model response is too short.
        """
        if retries == 0:
            print("[✗] Reached maximum retries. Returning last known good state.")
            return self.get_state_raw()

        state = self.get_state_raw()

        cached = self.llm_cache.get(self.last_action)
        if cached:
            print("\033[93m[CACHE] Using cached LLM result.\033[0m")
            return cached

        trained_categories = {
            "target": {"os", "services"},
            "web_directories_status": None
        }
        remove_untrained_categories(state, trained_categories)

        cached_inner_prompt = self.command_llm_cache.get(self.last_action)
        if cached_inner_prompt:
            inner_prompt = cached_inner_prompt
            print("\033[96m[PROMPT CACHE] Using cached inner prompt.\033[0m")
        else:
            prompt_for_prompt = PROMPT_FOR_A_PROMPT(command_output)
            inner_prompt = self.model.run([prompt_for_prompt])[0]
            self.command_llm_cache.set(self.last_action, inner_prompt)

        final_prompt = PROMPT_2(command_output, inner_prompt)

        responses = self.model.run([final_prompt])

        if responses and isinstance(responses, list) and len(responses) > 0:
            full_response = responses[0].strip()
            if len(full_response) >= 20:
                print(f"[✓] Model returned valid response with {len(full_response)} characters.")
            else:
                print(f"[✗] Response too short ({len(full_response)} characters). Retrying... (retries left: {retries-1})")
                return self.parse_output(command_output, retries=retries-1)
        else:
            print("[✗] Model run failed or empty response. Retrying...")
            return self.parse_output(command_output, retries=retries-1)

        print(f"full_response - {full_response}")

        parsed, data_for_cache = fix_json(self.last_state, full_response)
        parsed = self.check_state(parsed)
        remove_untrained_categories(parsed, trained_categories)

        data_for_cache = self.check_state(data_for_cache)
        remove_untrained_categories(data_for_cache, trained_categories)

        if parsed is None:
            print("⚠️ parsed is None – skipping this round safely.")
            return self.get_state_raw()

        if data_for_cache:
            self.llm_cache.set(self.last_action, data_for_cache)

        return parsed

    def clean_output(self, command_output: str) -> dict:
        """
        Clean long noisy outputs using a cleanup prompt and the LLM.
        """
        return self.model.run_prompt(clean_output_prompt(command_output))

    def update_policy(self, state, action, reward, next_state):
        """
        Manually trigger an update to the Q-network.
        """
        self.policy_model.update({
            "state": state,
            "action": self.action_space.index(action),
            "reward": reward,
            "next_state": next_state
        })

    def check_state(self, current_state: str):
        # Validate and correct the state
        new_state = validate_state(current_state)
        print(f"validate_state: {new_state}")
        
        # Correct the state based on predefined rules
        new_state = correct_state(new_state, self.os_linux_dataset, self.os_linux_kernel_dataset)
        print(f"correct_state: {new_state}")

        # Ensure the state is a dictionary
        if not isinstance(new_state, dict):
            print(f"[!] Warning: Invalid state type received. Converting to dictionary...")
            new_state = dict(new_state)
        
        new_state = sort_state(new_state)
        print(f"sort_state: {new_state}")

        return new_state
