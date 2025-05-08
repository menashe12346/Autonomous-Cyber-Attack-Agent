import torch
import torch.nn as nn
import torch.optim as optim
import copy
import random
import matplotlib.pyplot as plt

class RLModelTrainer:
    """
    A trainer class for reinforcement learning using Q-learning with experience replay.
    Supports prioritized experience buffers and a target network for stable learning.
    """

    def __init__(self, policy_model, replay_buffer, device='cpu', learning_rate=5e-4, gamma=0.99):
        """
        Initialize the trainer.

        Args:
            policy_model (nn.Module): The main Q-network.
            replay_buffer: Experience replay buffer.
            device (str): 'cpu' or 'cuda'.
            learning_rate (float): Optimizer learning rate.
            gamma (float): Discount factor for future rewards.
        """
        self.policy_model = policy_model.to(device)
        self.replay_buffer = replay_buffer
        self.device = device
        self.gamma = gamma

        self.optimizer = optim.Adam(self.policy_model.parameters(), lr=learning_rate)
        self.loss_fn = nn.SmoothL1Loss()

        self.training_history = []
        self.target_model = copy.deepcopy(policy_model).to(device)
        self.target_model.eval()

        self.update_target_steps = 100
        self.train_step = 0

        self.episode_rewards = []

        self.episode_epsilons = []

    def train_batch(self, batch_size):
        """
        Sample a batch from the replay buffer and update the policy model.

        Args:
            batch_size (int): Number of experiences to train on.

        Returns:
            float or None: The loss value, or None if buffer too small.
        """
        if self.replay_buffer.size() < batch_size:
            return None  # Not enough data yet

        states, actions, rewards, next_states, dones, weights, indices = self.replay_buffer.sample_batch(batch_size)

        # Move tensors to device
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)
        weights = torch.tensor(weights, dtype=torch.float32).to(self.device)

        # Q(s, a)
        q_values = self.policy_model.forward(states)
        current_q_values = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)

        # max_a' Q(next_state, a')
        next_q_values = self.target_model.forward(next_states)
        max_next_q_values = next_q_values.max(1)[0]
        dones = dones.float()
        td_target = rewards + self.gamma * max_next_q_values * (1 - dones)
        td_target = td_target.detach()

        # TD Error & loss
        td_errors = (current_q_values - td_target) ** 2
        td_errors = torch.clamp(td_errors, max=10.0)
        loss = (weights * td_errors).mean()

        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Update target model if needed
        self.train_step += 1
        # Dynamic tau increases with training steps

        #tau = min(0.005 + 0.0002 * self.train_step, 0.05)
        tau = 0.001 

        # Perform soft update
        for target_param, policy_param in zip(self.target_model.parameters(), self.policy_model.parameters()):
            target_param.data.copy_(tau * policy_param.data + (1.0 - tau) * target_param.data)

        # Update priorities
        self.replay_buffer.update_priorities(indices, td_errors.detach().cpu().numpy())

        self.training_history.append(loss.item())
        return loss.item()

    def evaluate_action(self, state):
        """
        Evaluate Q-values for all actions given a state (no learning).

        Args:
            state (list or Tensor): Input state.

        Returns:
            ndarray: Q-values for each action.
        """
        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(self.device)
            q_values = self.policy_model.forward(state_tensor)
            return q_values.cpu().numpy()

    def save_model(self, path):
        """
        Save the policy model to a file.

        Args:
            path (str): File path to save model.
        """
        torch.save(self.policy_model.state_dict(), path)

    def load_model(self, path):
        """
        Load the policy model from a file.

        Args:
            path (str): File path to load model from.
        """
        self.policy_model.load_state_dict(torch.load(path, map_location=self.device))
        self.policy_model.eval()

    def record_episode_reward(self, total_reward):
        """
        Records the total reward obtained in one episode.
        
        Args:
            total_reward (float): Sum of rewards during the episode.
        """
        self.episode_rewards.append(total_reward)
    
    def record_episode_epsilon(self, epsilon_value):
        self.episode_epsilons.append(epsilon_value)  # <-- חדש: לשמור גם את ערך epsilon אחרי כל פרק

    def plot_training_progress(self):
        """
        Plot the training loss curve, episode reward curve, and epsilon decay curve.
        """
        if not self.training_history and not self.episode_rewards:
            print("No training history or rewards to plot.")
            return

        episodes = list(range(1, len(self.episode_rewards) + 1))
        train_steps = list(range(1, len(self.training_history) + 1))

        plt.figure(figsize=(18, 5))

        # Plot loss
        plt.subplot(1, 3, 1)
        plt.plot(train_steps, self.training_history, label="Loss", color="red")
        plt.xlabel("Training Steps")
        plt.ylabel("Loss")
        plt.title("Training Loss Curve")
        plt.grid(True)
        plt.legend()

        # Plot reward
        plt.subplot(1, 3, 2)
        plt.plot(episodes, self.episode_rewards, label="Reward", color="green")
        plt.xlabel("Episode")
        plt.ylabel("Total Reward")
        plt.title("Episode Rewards Curve")
        plt.grid(True)
        plt.legend()

        # Plot epsilon
        if self.episode_epsilons:
            plt.subplot(1, 3, 3)
            plt.plot(episodes, self.episode_epsilons, label="Epsilon", color="blue")
            plt.xlabel("Episode")
            plt.ylabel("Epsilon")
            plt.title("Epsilon Decay Curve")
            plt.grid(True)
            plt.legend()

        plt.tight_layout()
        plt.show()
