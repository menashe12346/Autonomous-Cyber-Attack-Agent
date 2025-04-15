import random
import subprocess
import json
from abc import ABC, abstractmethod

from Cache.llm_cache import LLMCache

from utils.prompts import PROMPT_1, PROMPT_2, clean_output_prompt, PROMPT_FOR_A_PROMPT
from utils.utils import remove_comments_and_empty_lines, extract_json_block, one_line
from utils.state_check.state_validator import validate_state
from utils.state_check.state_correctness import correct_state

class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the attack environment.
    Provides the main learning and acting loop, caching, output parsing, and interaction with the blackboard.
    """

    def __init__(self, name, action_space, blackboard_api, replay_buffer,
                 policy_model, state_encoder, action_encoder, command_cache, model, epsilon=0.1):
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
        self.actions_history = []
        self.last_state = None
        self.last_action = None
        self.llm_cache = LLMCache(state_encoder=state_encoder)

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
        # Step 1: get state
        raw_state = self.get_state_raw()
        raw_state_with_history = dict(raw_state)
        raw_state_with_history["actions_history"] = self.actions_history.copy()
        state = self.state_encoder.encode(raw_state_with_history, self.actions_history)
        self.last_state = state

        print(f"last state: {json.dumps(raw_state_with_history, indent=2)}")

        # Step 2: select action
        action = self.choose_action(state)
        self.last_action = action
        self.actions_history.append(action)

        print(f"\n[+] Agent: {self.name}")
        print(f"    Current state: {str(state)[:8]}...")
        print(f"    Chosen action: {action}")

        # Step 3: execute action
        result = remove_comments_and_empty_lines(self.perform_action(action))
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
        print(f"parsed_info - {parsed_info}")

        parsed_info = self.check_state(parsed_info)
        print("correct_state: {parsed_info}")

        self.blackboard_api.overwrite_blackboard(parsed_info)

        # Step 6: observe next state
        raw_next_state = self.get_state_raw()
        raw_next_state_with_history = dict(raw_next_state)
        raw_next_state_with_history["actions_history"] = self.actions_history.copy()
        next_state = self.state_encoder.encode(raw_next_state_with_history, self.actions_history)

        # Step 7: reward and update model
        reward = self.get_reward(state, action, next_state)
        print(f"new state: {json.dumps(dict(self.state_encoder.decode(next_state)), indent=2)}")

        experience = {
            "state": state,
            "action": self.action_space.index(action),
            "reward": reward,
            "next_state": next_state
        }

        q_pred, loss = self.policy_model.update(experience)

        print(f"    Predicted Q-value: {q_pred:.4f}")
        print(f"    Actual reward:     {reward:.4f}")
        print(f"    Loss:              {loss:.6f}")

        # Step 8: save experience
        self.replay_buffer.add_experience(state, self.action_space.index(action), reward, next_state, False)

        # Step 9: log action
        self.blackboard_api.append_action_log({
            "agent": self.name,
            "action": action,
            "result": result,
        })

    def choose_action(self, state_vector):
        """
        ε-greedy policy: choose random action with probability ε, else best predicted action.
        """
        if random.random() < self.epsilon:
            action_index = random.randint(0, len(self.action_space) - 1)
            self.decay_epsilon()
        else:
            action_index = self.policy_model.predict_best_action(state_vector)

        return self.action_space[action_index]

    def decay_epsilon(self, decay_rate=0.995, min_epsilon=0.01):
        """
        Gradually reduce exploration probability.
        """
        self.epsilon = max(self.epsilon * decay_rate, min_epsilon)

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

    def parse_output(self, command_output: str) -> dict:
        """
        Parse command output using the LLM. Use cache if available.
        """
        raw_state = self.get_state_raw()
        raw_state["actions_history"] = self.actions_history.copy()

        cached = self.llm_cache.get(raw_state, self.last_action)
        if cached:
            print("\033[93m[CACHE] Using cached LLM result.\033[0m")
            return cached

        prompt_for_prompt = PROMPT_FOR_A_PROMPT(command_output)
        inner_prompt = self.model.run([prompt_for_prompt])[0]
        final_prompt = PROMPT_2(command_output, inner_prompt)

        responses = self.model.run([
            one_line(PROMPT_1(json.dumps(self.get_state_raw(), indent=2))),
            one_line(final_prompt)
        ])
        
        full_response = responses[1] + "\n" + responses[0]
        print(f"full_response - {full_response}")

        parsed = extract_json_block(full_response)
        if parsed:
            self.llm_cache.set(raw_state, self.last_action, parsed)

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
        new_state = validate_state(current_state)
        new_state = correct_state(new_state)
        return new_state