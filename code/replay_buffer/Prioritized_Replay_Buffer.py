import random
import numpy as np
import torch


class PrioritizedReplayBuffer:
    def __init__(self, max_size=100_000, alpha=0.6, beta=0.4):
        """
        A prioritized experience replay buffer for deep Q-learning.

        Args:
            max_size (int): Maximum number of experiences to store.
            alpha (float): Priority exponent (how much prioritization is used).
            beta (float): Importance-sampling exponent (how much to correct for bias).
        """
        self.max_size = max_size
        self.alpha = alpha
        self.beta = beta

        self.buffer = []
        self.priorities = []

    def add_experience(self, state, action, reward, next_state, done):
        """
        Add a new experience to the buffer with maximum priority.

        Args:
            state (Tensor): Current state.
            action (int): Action taken.
            reward (float): Reward received.
            next_state (Tensor): Next state.
            done (bool): Whether the episode ended.
        """
        max_priority = max(self.priorities) if self.buffer else 1.0
        experience = {
            "state": state,
            "action": action,
            "reward": reward,
            "next_state": next_state,
            "done": done
        }

        if len(self.buffer) >= self.max_size:
            self.buffer.pop(0)
            self.priorities.pop(0)

        self.buffer.append(experience)
        self.priorities.append(max_priority)

    def sample_batch(self, batch_size):
        """
        Sample a batch of experiences according to their priority.

        Args:
            batch_size (int): Number of experiences to sample.

        Returns:
            Tuple of tensors: (states, actions, rewards, next_states, dones, weights, indices)
        """
        if len(self.buffer) == 0:
            raise ValueError("The replay buffer is empty.")

        priorities = np.array(self.priorities, dtype=np.float32)
        scaled_priorities = priorities ** self.alpha
        sampling_probs = scaled_priorities / scaled_priorities.sum()

        indices = np.random.choice(len(self.buffer), size=batch_size, p=sampling_probs)
        experiences = [self.buffer[i] for i in indices]

        weights = (len(self.buffer) * sampling_probs[indices]) ** -self.beta
        weights = weights / weights.max()

        states = torch.stack([exp["state"] for exp in experiences])
        actions = torch.tensor([exp["action"] for exp in experiences])
        rewards = torch.tensor([exp["reward"] for exp in experiences])
        next_states = torch.stack([exp["next_state"] for exp in experiences])
        dones = torch.tensor([exp["done"] for exp in experiences])

        return states, actions, rewards, next_states, dones, torch.tensor(weights, dtype=torch.float32), indices

    def update_priorities(self, indices, new_priorities):
        """
        Update the priority of sampled experiences.

        Args:
            indices (List[int]): Indices of the sampled experiences.
            new_priorities (List[float]): Updated priority values.
        """
        for idx, priority in zip(indices, new_priorities):
            self.priorities[idx] = max(priority, 1e-5)
            
    def size(self):
        """
        Return the number of stored experiences.
        """
        return len(self.buffer)

    def clear(self):
        """
        Clear all experiences and priorities.
        """
        self.buffer.clear()
        self.priorities.clear()
