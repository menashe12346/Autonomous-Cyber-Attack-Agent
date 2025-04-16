import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import TARGET_IP, LLAMA_RUN, MODEL_PATH, CVE_PATH
from blackboard.blackboard import initialize_blackboard
from blackboard.api import BlackboardAPI
from agents.recon_agent import ReconAgent
from agents.vuln_agent import VulnAgent
from models.policy_model import PolicyModel
from replay_buffer.Prioritized_Replay_Buffer import PrioritizedReplayBuffer
from encoders.state_encoder import StateEncoder
from encoders.action_encoder import ActionEncoder
from tools.action_space import get_commands_for_agent
from models.llm.llama_interface import LlamaModel

def debug_one_step():
    print("[*] Starting one-step debug...")

    # שלב 1: אתחול LLM
    model = LlamaModel(LLAMA_RUN, MODEL_PATH)

    # שלב 2: אתחול לוח שחור
    bb_dict = initialize_blackboard()
    bb_dict["target"]["ip"] = TARGET_IP
    bb_api = BlackboardAPI(bb_dict)

    # שלב 3: אתחול כלים נדרשים ל-ReconAgent
    action_space = get_commands_for_agent("recon", TARGET_IP)
    state_encoder = StateEncoder(action_space)
    action_encoder = ActionEncoder(action_space)
    policy_model = PolicyModel(state_size=128, action_size=len(action_space))
    replay_buffer = PrioritizedReplayBuffer(max_size=1000)

    # שלב 4: צרי את הסוכנים
    recon_agent = ReconAgent(
        blackboard_api=bb_api,
        policy_model=policy_model,
        replay_buffer=replay_buffer,
        state_encoder=state_encoder,
        action_encoder=action_encoder,
        command_cache={},
        model=model
    )

    vuln_agent = VulnAgent(
        blackboard_api=bb_api,
        vuln_db_path=CVE_PATH
    )

    # שלב 5: הרץ רק צעד אחד של Recon ואז Vuln
    if recon_agent.should_run():
        recon_agent.run()
    vuln_agent.run()

    # הדפסת מצב הסופי
    print("\n[DEBUG] Final blackboard state:")
    import json
    print(json.dumps(bb_api.get_state_for_agent("ReconAgent"), indent=2))

if __name__ == "__main__":
    debug_one_step()
