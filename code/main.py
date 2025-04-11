import torch
from blackboard.blackboard import initialize_blackboard
from blackboard.api import BlackboardAPI
from replay_buffer.Prioritized_Replay_Buffer import PrioritizedReplayBuffer
from agents.agent_manager import AgentManager
from orchestrator.scenario_orchestrator import ScenarioOrchestrator
from models.policy_model import PolicyModel
from models.trainer import RLModelTrainer
from encoders.state_encoder import StateEncoder
from encoders.action_encoder import ActionEncoder
from tools.action_space import get_commands_for_agent
from agents.recon_agent import ReconAgent
from models.LoadModel import LoadModel

def main():
    NUM_EPISODES = 3000
    MAX_STEPS_PER_EPISODE = 5
    LLAMA_RUN = "/mnt/linux-data/project/code/models/llama.cpp/build/bin/llama-run" # change to your path
    MODEL_PATH = "file:///mnt/linux-data/project/code/models/nous-hermes/Nous-Hermes-2-Mistral-7B-DPO.Q4_K_M.gguf" # change to your path
    model = LoadModel(LLAMA_RUN, MODEL_PATH)
    TARGET_IP = "192.168.56.101"

    # אתחול Replay Buffer משותף לכל הפרקים
    replay_buffer = PrioritizedReplayBuffer(max_size=20000)

    # אתחול Action Space קבוע מראש (לפי IP קבוע)
    action_space = get_commands_for_agent("recon", TARGET_IP)
    action_encoder = ActionEncoder(action_space)
    state_encoder = StateEncoder(action_space=action_space)

    # אתחול Policy Model
    state_size = 128
    action_size = len(action_space)
    policy_model = PolicyModel(state_size=state_size, action_size=action_size)

    # מעבר ל־GPU אם זמין
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy_model.to(device)

    # אתחול מאמן RL
    trainer = RLModelTrainer(policy_model, replay_buffer, device=device, learning_rate=1e-3, gamma=0.99)

    command_cache = {}

    all_actions = []  # רשימת כל הפעולות של כל האפיזודות

    # הרצת מספר פרקים (סימולציות)
    for episode in range(NUM_EPISODES):
        print(f"\n========== EPISODE {episode + 1} ==========")

        # אתחול מחדש של ה־Blackboard לפרק נפרד
        blackboard_dict = initialize_blackboard()
        blackboard_dict["target"]["ip"] = TARGET_IP
        bb_api = BlackboardAPI(blackboard_dict)

        # יצירת הסוכן מחדש (state פנימי חדש בכל פעם)
        recon_agent = ReconAgent(
            blackboard_api=bb_api,
            policy_model=policy_model,
            replay_buffer=replay_buffer,
            state_encoder=state_encoder,
            action_encoder=action_encoder,
            command_cache = command_cache,
            model = model
        )

        agents = [recon_agent]
        agent_manager = AgentManager(bb_api)
        agent_manager.register_agents(agents)

        orchestrator = ScenarioOrchestrator(
            blackboard=bb_api,
            agent_manager=agent_manager,
            max_steps=MAX_STEPS_PER_EPISODE,
            scenario_name=f"AttackEpisode_{episode + 1}",
            target=TARGET_IP
        )

        orchestrator.run_scenario_loop()

        all_actions.append({
            "episode": episode + 1,
            "actions": recon_agent.actions_history.copy()
        })

        # שלב אימון קצר אחרי כל פרק (אפשר גם כל כמה פרקים)
        for _ in range(10):  # למשל 10 איטרציות אימון
            loss = trainer.train_batch(batch_size=32)
            if loss is not None:
                print(f"[Episode {episode + 1}] Training loss: {loss:.4f}")
    
    print("\n========== SUMMARY OF ALL EPISODES ==========")
    #for episode_info in all_actions:
        #print(f"Episode {episode_info['episode']}: {episode_info['actions']}")

    # שמירה סופית של המודל
    trainer.save_model("models/saved_models/policy_model.pth")
    print("✅ Final trained model saved.")

if __name__ == "__main__":
    main()
