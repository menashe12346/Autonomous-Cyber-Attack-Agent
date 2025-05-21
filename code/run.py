import torch
from config import (
    TARGET_IP, MISTRAL_MODEL_PATH,
    DATASET_NVD_CVE_PATH, DATASET_OS_LINUX, DATASET_OS_LINUX_KERNEL,
    DATASET_METASPLOIT, DATASET_EXPLOITDB_CVE_EXPLOIT_PATH, DATASET_EXPLOIT
)

from blackboard.blackboard import initialize_blackboard
from blackboard.api import BlackboardAPI
from agents.agent_manager import AgentManager
from agents.recon_agent import ReconAgent
from agents.vuln_agent import VulnAgent
from agents.exploit_agent import ExploitAgent
from orchestrator.scenario_orchestrator import ScenarioOrchestrator

from models.policy_model import PolicyModel
from models.llm.llama_interface import LlamaModel

from encoders.state_encoder import StateEncoder
from encoders.action_encoder import ActionEncoder

from tools.action_space import get_commands_for_agent
from utils.utils import load_dataset
from create_datasets.create_exploit_dataset.create_full_exploit_dataset import merge_exploit_datasets


def run_evaluation():
    print("[*] Loading model and datasets...")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load datasets
    cve_items = load_dataset(DATASET_NVD_CVE_PATH)
    metasploit_dataset = load_dataset(DATASET_METASPLOIT)
    exploitdb_dataset = load_dataset(DATASET_EXPLOITDB_CVE_EXPLOIT_PATH)
    os_linux_dataset = load_dataset(DATASET_OS_LINUX)
    os_linux_kernel_dataset = load_dataset(DATASET_OS_LINUX_KERNEL)

    full_exploit_dataset = merge_exploit_datasets(metasploit_dataset, exploitdb_dataset, DATASET_EXPLOIT)

    # Load LLM
    model = LlamaModel()

    # Blackboard
    blackboard_dict = initialize_blackboard(TARGET_IP)
    bb_api = BlackboardAPI(blackboard_dict)

    # === Recon Agent ===
    recon_action_space = get_commands_for_agent("recon")
    recon_action_encoder = ActionEncoder(recon_action_space)
    recon_state_encoder = StateEncoder(recon_action_space)
    recon_model = PolicyModel(state_size=1024, action_size=len(recon_action_space)).to(device)
    recon_model.load_state_dict(torch.load("models/saved_models/recon_model.pth", map_location=device))
    recon_model.eval()

    recon_agent = ReconAgent(
        blackboard_api=bb_api,
        policy_model=recon_model,
        replay_buffer=None,
        state_encoder=recon_state_encoder,
        action_encoder=recon_action_encoder,
        command_cache={},
        model=model,
        epsilon=0.0,
        os_linux_dataset=os_linux_dataset,
        os_linux_kernel_dataset=os_linux_kernel_dataset
    )

    # === Vuln Agent ===
    vuln_agent = VulnAgent(
        blackboard_api=bb_api,
        cve_items=cve_items,
        epsilon=0.0,
        os_linux_dataset=os_linux_dataset,
        os_linux_kernel_dataset=os_linux_kernel_dataset,
        metasploit_dataset=metasploit_dataset
    )

    # === Exploit Agent ===
    exploit_action_space = list({v["cve"] for v in metasploit_dataset if "cve" in v})
    exploit_action_encoder = ActionEncoder(exploit_action_space)
    exploit_state_encoder = StateEncoder(exploit_action_space)
    exploit_model = PolicyModel(state_size=1024, action_size=len(exploit_action_space)).to(device)
    exploit_model.load_state_dict(torch.load("models/saved_models/exploit_model.pth", map_location=device))
    exploit_model.eval()

    exploit_agent = ExploitAgent(
        blackboard_api=bb_api,
        policy_model=exploit_model,
        replay_buffer=None,
        state_encoder=exploit_state_encoder,
        action_encoder=exploit_action_encoder,
        command_cache={},
        model=model,
        epsilon=0.0,
        metasploit_dataset=metasploit_dataset,
        exploitdb_dataset=exploitdb_dataset,
        full_exploit_dataset=full_exploit_dataset,
        os_linux_dataset=os_linux_dataset,
        os_linux_kernel_dataset=os_linux_kernel_dataset
    )

    # === Scenario ===
    manager = AgentManager(bb_api)
    manager.register_agents([recon_agent, vuln_agent, exploit_agent])

    orchestrator = ScenarioOrchestrator(
        blackboard=bb_api,
        agent_manager=manager,
        scenario_name="EvaluationEpisode",
        target=TARGET_IP
    )

    print("\n🚀 Running one evaluation episode (no training)...")
    orchestrator.run_scenario_loop()


if __name__ == "__main__":
    run_evaluation()
