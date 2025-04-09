import random
import numpy as np
import torch

class PrioritizedReplayBuffer:
    def __init__(self, max_size=100000, alpha=0.6, beta=0.4):
        self.max_size = max_size
        self.alpha = alpha  # alpha קובע את עוצמת ה-priorities
        self.beta = beta    # beta קובע עד כמה נעדיף חוויות עם priorites גבוהים
        self.buffer = []
        self.priorities = []

    def add_experience(self, state, action, reward, next_state, done):
        """
        מוסיף ניסיון חדש למאגר עם priority.
        """
        priority = max(self.priorities) if self.buffer else 1.0  # אתחול priority
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
        self.priorities.append(priority)

    def sample_batch(self, batch_size):
        """
        מחזיר דגימה אקראית של חוויות מהמאגר לפי עדיפות.
        """
        priorities = np.array(self.priorities)
        scaled_priorities = priorities ** self.alpha
        probabilities = scaled_priorities / np.sum(scaled_priorities)

        indices = np.random.choice(len(self.buffer), size=batch_size, p=probabilities)
        batch = [self.buffer[i] for i in indices]
        weights = (len(self.buffer) * probabilities[indices]) ** -self.beta
        weights /= weights.max()

        states = torch.stack([ex['state'] for ex in batch])
        actions = torch.tensor([ex['action'] for ex in batch])
        rewards = torch.tensor([ex['reward'] for ex in batch])
        next_states = torch.stack([ex['next_state'] for ex in batch])
        dones = torch.tensor([ex['done'] for ex in batch])

        return states, actions, rewards, next_states, dones, weights, indices

    def update_priorities(self, indices, priorities):
        """
        מעדכן את ה-priorities של חוויות מסוימות לפי חוויות מאוחרות.
        """
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority

    def size(self):
        return len(self.buffer)

    def clear(self):
        self.buffer.clear()
        self.priorities.clear()
