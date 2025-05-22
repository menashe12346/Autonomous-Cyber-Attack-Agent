import torch
import os
import urllib.parse

from config import (
    # Reinforcement Learning parameters
    NUM_EPISODES,
    MAX_ENCODING_FEATURES,
    EPSILON,

    # LLM configuration
    MISTRAL_MODEL_PATH,

    # Target configuration
    TARGET_IP,

    # CVE paths
    DATASET_NVD_CVE_PATH,

    # Exploit datasets
    DATASET_EXPLOITDB_CVE_EXPLOIT_PATH,
    DATASET_METASPLOIT,
    DATASET_EXPLOIT,

    # Linux-related datasets
    DATASET_OS_LINUX,
    DATASET_OS_LINUX_KERNEL
)

from blackboard.blackboard import initialize_blackboard
from blackboard.api import BlackboardAPI

from replay_buffer.Prioritized_Replay_Buffer import PrioritizedReplayBuffer

from agents.agent_manager import AgentManager
from agents.recon_agent import ReconAgent
from agents.vuln_agent import VulnAgent
from agents.exploit_agent import ExploitAgent

from orchestrator.scenario_orchestrator import ScenarioOrchestrator

from models.policy_model import PolicyModel
from models.trainer import RLModelTrainer
from models.llm.llama_interface import LlamaModel

from encoders.state_encoder import StateEncoder
from encoders.action_encoder import ActionEncoder

from tools.action_space import get_commands_for_agent

from utils.utils import load_dataset, check_file_exists

from create_datasets.create_cve_dataset.download_combine_nvd_cve import download_nvd_cve
from create_datasets.create_cve_dataset.create_cve_cpe_dataset import create_cve_cpe_dataset

from create_datasets.create_exploit_dataset.download_exploitdb import download_exploitdb
from create_datasets.create_exploit_dataset.create_exploitPath_cve_dataset import create_cve_exploitdb_dataset
from create_datasets.create_exploit_dataset.create_metasploit_dataset import create_metasploit_dataset
from create_datasets.create_exploit_dataset.download_metasploit import download_metasploit
from create_datasets.create_exploit_dataset.create_full_exploit_dataset import merge_exploit_datasets

from create_datasets.create_os_dataset.distrowatch import download_os_linux_dataset

def main():

    # Check mistral llm model exists
    try:
        check_file_exists(MISTRAL_MODEL_PATH)
    except Exception as e:
        print(e)
        exit(1)

    # LLM Model
    model = LlamaModel()

    # Download nvd cve dataset
    download_nvd_cve()

    # Download exploitdb dataset
    download_exploitdb()

    # Download metasploit
    download_metasploit()

    # Create nvd cve cpe dataset
    create_cve_cpe_dataset()

    # Create exploitdb (cve, exploit path) dataset
    create_cve_exploitdb_dataset()

    # Create metasploit dataset
    create_metasploit_dataset()

    # Download and Create os Linux dataset
    download_os_linux_dataset()

    # Load cve dataset
    cve_items = load_dataset(DATASET_NVD_CVE_PATH)
    print(f"✅ CVE dataset Loaded Successfully")

    # Load metasploit dataset
    metasploit_dataset = load_dataset(DATASET_METASPLOIT)
    print(f"✅ Metasploit dataset Loaded Successfully")

    # Load exploitdb dataset
    exploitdb_dataset = load_dataset(DATASET_EXPLOITDB_CVE_EXPLOIT_PATH)
    print(f"✅ ExploitDB dataset Loaded Successfully")

    # Create exploit_dataset that consists metasploit and exploitdb datasets
    full_exploit_dataset = merge_exploit_datasets(metasploit_dataset, exploitdb_dataset, DATASET_EXPLOIT)
    print(f"✅ Full exploit dataset Loaded Successfully")

    os_linux_dataset = load_dataset(DATASET_OS_LINUX)
    print(f"✅ OS Linux dataset Loaded Successfully")

    os_linux_kernel_dataset = load_dataset(DATASET_OS_LINUX_KERNEL)
    print(f"✅ OS Linux Kernel dataset Loaded Successfully")

    # Move to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # --- RECON POLICY ---
    recon_action_space = get_commands_for_agent("recon")
    recon_action_encoder = ActionEncoder(recon_action_space)
    recon_state_encoder = StateEncoder(action_space=recon_action_space)
    recon_policy_model = PolicyModel(state_size=MAX_ENCODING_FEATURES, action_size=len(recon_action_space))
    recon_policy_model.to(device)
    recon_replay_buffer = PrioritizedReplayBuffer(max_size=20000)

    recon_trainer = RLModelTrainer(
        policy_model=recon_policy_model,
        replay_buffer=recon_replay_buffer,
        device=device,
        learning_rate=1e-3,
        gamma=0.99
    )

    # --- EXPLOIT POLICY ---
    exploit_action_space = list({v["cve"] for v in metasploit_dataset if "cve" in v})
    exploit_action_encoder = ActionEncoder(exploit_action_space)
    exploit_state_encoder = StateEncoder(action_space=exploit_action_space)
    exploit_policy_model = PolicyModel(state_size=MAX_ENCODING_FEATURES, action_size=len(exploit_action_space))
    exploit_policy_model.to(device)
    exploit_replay_buffer = PrioritizedReplayBuffer(max_size=20000)

    exploit_trainer = RLModelTrainer(
        policy_model=exploit_policy_model,
        replay_buffer=exploit_replay_buffer,
        device=device,
        learning_rate=1e-3,
        gamma=0.99
    )


    command_cache = {}
    all_actions = []
    epsilon = EPSILON

    # === EPISODE LOOP ===
    for episode in range(NUM_EPISODES):
        print(f"\n========== EPISODE {episode + 1} ==========")

        # --- Initialize Blackboard ---
        blackboard_dict = initialize_blackboard(TARGET_IP)
        bb_api = BlackboardAPI(blackboard_dict)

        # --- Create Recon Agent ---
        recon_agent = ReconAgent(
            blackboard_api=bb_api,
            policy_model=recon_policy_model,
            replay_buffer=recon_replay_buffer,
            state_encoder=recon_state_encoder,
            action_encoder=recon_action_encoder,
            command_cache=command_cache,
            model=model,
            epsilon=epsilon,
            os_linux_dataset=os_linux_dataset,
            os_linux_kernel_dataset=os_linux_kernel_dataset
        )
        
        # --- Create vuln Agent ---
        vuln_agent = VulnAgent(
            blackboard_api=bb_api,
            cve_items=cve_items,
            epsilon= epsilon,
            os_linux_dataset=os_linux_dataset,
            os_linux_kernel_dataset=os_linux_kernel_dataset,
            metasploit_dataset=metasploit_dataset,
        )

        # --- Create exploit Agent ---
        exploit_agent = ExploitAgent(
            blackboard_api=bb_api,
            policy_model=exploit_policy_model,
            replay_buffer=exploit_replay_buffer,
            state_encoder=exploit_state_encoder,
            action_encoder=exploit_action_encoder,
            command_cache=command_cache,
            model=model,
            metasploit_dataset=metasploit_dataset,
            exploitdb_dataset=exploitdb_dataset,
            full_exploit_dataset=full_exploit_dataset,
            epsilon=0.1,
            os_linux_dataset=os_linux_dataset,
            os_linux_kernel_dataset=os_linux_kernel_dataset
        )

        # --- Register Agents ---
        agents = [recon_agent, vuln_agent, exploit_agent] 
        #agents = [recon_agent]
        agent_manager = AgentManager(bb_api)
        agent_manager.register_agents(agents)

        # --- Run Scenario ---
        scenario_name = f"AttackEpisode_{episode + 1}"
        orchestrator = ScenarioOrchestrator(
            blackboard=bb_api,
            agent_manager=agent_manager,
            scenario_name=scenario_name,
            target=TARGET_IP
        )
        orchestrator.run_scenario_loop()

        # --- Track actions taken ---
        all_actions.append({
            "episode": episode + 1,
            "actions": recon_agent.actions_history.copy()
        })

        # --- Track Reward ---
        if hasattr(recon_agent, "episode_total_reward"):
            recon_trainer.record_episode_reward(recon_agent.episode_total_reward)
            recon_agent.decay_epsilon()
            recon_trainer.record_episode_epsilon(recon_agent.epsilon)
            epsilon = recon_agent.epsilon
        
        # --- Track Reward for Exploit Agent ---
        if hasattr(exploit_agent, "episode_total_reward"):
            exploit_trainer.record_episode_reward(exploit_agent.episode_total_reward)
            exploit_agent.decay_epsilon()
            exploit_trainer.record_episode_epsilon(exploit_agent.epsilon)


        # --- Train Policy Model ---
        # אימון של שניהם
        for _ in range(10):
            recon_loss = recon_trainer.train_batch(batch_size=32)
            exploit_loss = exploit_trainer.train_batch(batch_size=32)

            if recon_loss is not None:
                print(f"[Episode {episode + 1}] Recon Loss: {recon_loss:.4f}")
            if exploit_loss is not None:
                print(f"[Episode {episode + 1}] Exploit Loss: {exploit_loss:.4f}")


    #print("\n========== SUMMARY OF ALL EPISODES ==========")
    #for episode_info in all_actions:
    #    print(f"Episode {episode_info['episode']}: {episode_info['actions']}")

    #recon_trainer.save_model("models/saved_models/recon_model.pth")
    #exploit_trainer.save_model("models/saved_models/exploit_model.pth")
    print("✅ Final trained model saved.")

    # --- Plot Training Curves ---
    recon_trainer.plot_training_progress()
    exploit_trainer.plot_training_progress()

if __name__ == "__main__":
    main()
