import torch
from config import NUM_EPISODES, MAX_STEPS_PER_EPISODE, LLAMA_RUN, MODEL_PATH, TARGET_IP, CVE_PATH

from blackboard.blackboard import initialize_blackboard
from blackboard.api import BlackboardAPI

from replay_buffer.Prioritized_Replay_Buffer import PrioritizedReplayBuffer

from agents.agent_manager import AgentManager
from agents.recon_agent import ReconAgent
from agents.vuln_agent import VulnAgent, load_cve_database

from orchestrator.scenario_orchestrator import ScenarioOrchestrator

from models.policy_model import PolicyModel
from models.trainer import RLModelTrainer
from models.llm.llama_interface import LlamaModel

from encoders.state_encoder import StateEncoder
from encoders.action_encoder import ActionEncoder

from tools.action_space import get_commands_for_agent

def main():

    # LLM Model
    model = LlamaModel(LLAMA_RUN, MODEL_PATH)

    # Load cve dataset
    cve_items = load_cve_database(CVE_PATH)
    print("✅ CVE dataset Loaded successfully.")

    # Replay Buffer
    replay_buffer = PrioritizedReplayBuffer(max_size=20000)

    # Action Space
    action_space = get_commands_for_agent("recon", TARGET_IP)
    action_encoder = ActionEncoder(action_space)
    state_encoder = StateEncoder(action_space=action_space)

    # Policy Model
    state_size = 128
    action_size = len(action_space)
    policy_model = PolicyModel(state_size=state_size, action_size=action_size)

    # Move to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy_model.to(device)

    # Trainer
    trainer = RLModelTrainer(
    policy_model=policy_model,
    replay_buffer=replay_buffer,
    device=device,
    learning_rate=1e-3,
    gamma=0.99
    )

    command_cache = {}
    all_actions = []

    # === EPISODE LOOP ===
    for episode in range(NUM_EPISODES):
        print(f"\n========== EPISODE {episode + 1} ==========")

        # --- Initialize Blackboard ---
        blackboard_dict = initialize_blackboard()
        blackboard_dict["target"]["ip"] = TARGET_IP
        bb_api = BlackboardAPI(blackboard_dict)

        # --- Create Recon Agent ---
        recon_agent = ReconAgent(
            blackboard_api=bb_api,
            policy_model=policy_model,
            replay_buffer=replay_buffer,
            state_encoder=state_encoder,
            action_encoder=action_encoder,
            command_cache=command_cache,
            model=model
        )
        
        # --- Create vuln Agent ---
        vuln_agent = VulnAgent(
            blackboard_api=bb_api,
            cve_items=cve_items
        )

        # --- Register Agents ---
        agents = [recon_agent, vuln_agent]
        agent_manager = AgentManager(bb_api)
        agent_manager.register_agents(agents)

        # --- Run Scenario ---
        scenario_name = f"AttackEpisode_{episode + 1}"
        orchestrator = ScenarioOrchestrator(
            blackboard=bb_api,
            agent_manager=agent_manager,
            max_steps=MAX_STEPS_PER_EPISODE,
            scenario_name=scenario_name,
            target=TARGET_IP
        )
        orchestrator.run_scenario_loop()

        # --- Track actions taken ---
        all_actions.append({
            "episode": episode + 1,
            "actions": recon_agent.actions_history.copy()
        })

        # --- Train Policy Model ---
        for _ in range(10):
            loss = trainer.train_batch(batch_size=32)
            if loss is not None:
                print(f"[Episode {episode + 1}] Training loss: {loss:.4f}")

    #print("\n========== SUMMARY OF ALL EPISODES ==========")
    #for episode_info in all_actions:
    #    print(f"Episode {episode_info['episode']}: {episode_info['actions']}")

    trainer.save_model("models/saved_models/policy_model.pth")
    print("✅ Final trained model saved.")

if __name__ == "__main__":
    main()
