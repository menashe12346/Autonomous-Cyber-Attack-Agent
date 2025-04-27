import torch
import os
from config import NUM_EPISODES, MAX_STEPS_PER_EPISODE, LLAMA_RUN, MODEL_PATH, TARGET_IP, CVE_PATH, NVD_CVE_PATH, PROJECT_PATH, EXPLOITDB_FILES_EXPLOITS_PATH, CVE_EXPLOIT_PATH, DATASETS_PATH, METASPLOIT_DATASET, METASPLOIT_PATH, EXPLOITDB_DATASET_PATH, EXPLOIT_DATASET

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

from utils.utils import load_dataset

from create_datasets.create_cve_dataset.download_combine_nvd_cve import download_nvd_cve
from create_datasets.create_exploit_dataset.download_exploitdb import download_exploitdb
from create_datasets.create_exploit_dataset.create_exploitPath_cve_dataset import create_cve_exploitdb_dataset
from create_datasets.create_exploit_dataset.create_metasploit_dataset import create_metasploit_dataset
from create_datasets.create_exploit_dataset.download_metasploit import download_metasploit
from create_datasets.create_exploit_dataset.create_full_exploit_dataset import merge_exploit_datasets
import urllib.parse

def strip_file_scheme(path):
    if path.startswith("file://"):
        return urllib.parse.urlparse(path).path
    return path

def check_llm_model_exists(min_size_gb=4):
    """
    מאמת שהקובץ קיים ושוקל לפחות 4GB. אחרת מעלה חריגה.

    Args:
        min_size_gb (int): גודל מינימלי בג'יגה־בייט (ברירת מחדל: 4).

    Raises:
        FileNotFoundError: אם הקובץ לא קיים.
        ValueError: אם הקובץ קטן מ־4GB.
    """
    model_path = strip_file_scheme(MODEL_PATH)

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"❌ File not found: {model_path}, please check README.md on how to download")

    size_bytes = os.path.getsize(model_path)
    size_gb = size_bytes / (1024 ** 3)

    if size_gb < min_size_gb:
        raise ValueError(f"❌ file size is lower then {min_size_gb}GB ({size_gb:.2f}GB): {model_path}, maybe corrupted, remove the file and run program again")
    
    print(f"✅ File {os.path.basename(model_path)} ({size_gb:.2f}GB) exists")

def main():

    # Check mistral llm model exists
    try:
        check_llm_model_exists()
    except Exception as e:
        print(e)
        exit(1)

    # LLM Model
    model = LlamaModel(LLAMA_RUN, MODEL_PATH)

    # Download nvd cve dataset
    download_nvd_cve(NVD_CVE_PATH, CVE_PATH)

    # Download exploitdb dataset
    download_exploitdb(DATASETS_PATH)

    # Download metasploit
    download_metasploit(METASPLOIT_PATH)

    # Create cve exploit dataset
    create_cve_exploitdb_dataset(EXPLOITDB_FILES_EXPLOITS_PATH, CVE_EXPLOIT_PATH)

    # Create metasploit dataset
    create_metasploit_dataset(METASPLOIT_DATASET)

    # Load metasploit dataset
    metasploit_dataset = load_dataset(METASPLOIT_DATASET)
    print(f"✅ Metasploit dataset Loaded Successfully")

    # Load exploitdb dataset
    exploitdb_dataset = load_dataset(EXPLOITDB_DATASET_PATH)
    print(f"✅ ExploitDB dataset Loaded Successfully")

    # Load cve dataset
    cve_items = load_dataset(CVE_PATH)
    print(f"✅ CVE dataset Loaded Successfully")

    full_exploit_dataset = merge_exploit_datasets(metasploit_dataset, exploitdb_dataset, EXPLOIT_DATASET)
    print(f"✅ Full exploit dataset Loaded Successfully")

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

        # --- Create exploit Agent ---
        exploit_agent = ExploitAgent(
            blackboard_api=bb_api,
            policy_model=policy_model,
            replay_buffer=replay_buffer,
            state_encoder=state_encoder,
            action_encoder=action_encoder,
            command_cache=command_cache,
            model=model,
            metasploit_dataset=metasploit_dataset,
            exploitdb_dataset=exploitdb_dataset,
            full_exploit_dataset=full_exploit_dataset
        )

        # --- Register Agents ---
        agents = [recon_agent] # , vuln_agent, exploit_agent
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
