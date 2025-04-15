# agents/llm_parser_agent.py

from agents.base_agent import BaseAgent
from utils.utils import extract_json_block
from utils.prompts import PROMPT_1, PROMPT_2, PROMPT_FOR_A_PROMPT
from utils.prompts import clean_output_prompt

class LLMParserAgent(BaseAgent):
    """
    Agent for parsing raw command outputs into structured blackboard-compatible JSON
    using a language model.
    """

    def __init__(self, blackboard_api, model):
        super().__init__(
            name="LLMParserAgent",
            action_space=[],  # No actions
            blackboard_api=blackboard_api,
            replay_buffer=None,
            policy_model=None,
            state_encoder=None,
            action_encoder=None,
            command_cache={},
            model=model
        )

    def should_run(self) -> bool:
        # Run if new raw output is present
        return bool(self.blackboard_api.blackboard.get("last_raw_output", ""))

    def get_reward(self, prev_state, action, next_state) -> float:
        # This agent doesn't participate in reward learning
        return 0.0

    def run(self):
        raw_output = self.blackboard_api.blackboard.get("last_raw_output", "")
        if not raw_output:
            print("[LLMParserAgent] No raw output to process.")
            return

        print("\n[+] LLMParserAgent running...")

        # 1. Create prompts
        prompt_for_prompt = PROMPT_FOR_A_PROMPT(raw_output)
        inner_prompt = self.model.run([prompt_for_prompt])[0]
        final_prompt = PROMPT_2(raw_output, inner_prompt)

        # 2. Run with context structure
        structure_prompt = PROMPT_1(self.blackboard_api.get_state_for_agent(self.name))
        responses = self.model.run([
            self.one_line(structure_prompt),
            self.one_line(final_prompt)
        ])

        # 3. Extract JSON
        full_response = responses[1] + "\n" + responses[0]
        print(f"[LLMParserAgent] full_response - {full_response}")

        parsed = extract_json_block(full_response)

        if parsed:
            # Post-fix structure if needed
            parsed = self.fix_json(parsed)
            print(f"[LLMParserAgent] Parsed JSON: {parsed}")
            self.blackboard_api.overwrite_blackboard(parsed)
        else:
            print("[LLMParserAgent] ❌ Failed to extract valid JSON.")

    def one_line(self, text: str) -> str:
        return ' '.join(line.strip() for line in text.strip().splitlines() if line).replace('  ', ' ')

    def fix_json(self, parsed: dict) -> dict:
        """
        Ensures the parsed JSON strictly follows expected format.
        """
        required_statuses = ["200", "401", "403", "404", "503"]
        wds = parsed.get("web_directories_status", {})
        for status in required_statuses:
            if status not in wds or not isinstance(wds[status], dict) or not wds[status]:
                wds[status] = {"": ""}
        parsed["web_directories_status"] = wds

        # Ensure services list has exactly 3 entries
        services = parsed.get("target", {}).get("services", [])
        while len(services) < 3:
            services.append({"port": "", "protocol": "", "service": ""})
        parsed["target"]["services"] = services[:3]

        return parsed
