import torch
import torch.nn as nn
import torch.optim as optim
import random
import copy  # בתחילת הקובץ

class RLModelTrainer:
    def __init__(self, policy_model, replay_buffer, device='cpu', learning_rate=1e-3, gamma=0.99):
        """
        מאמן את מודל ה־policy (Q-Network) לפי נתונים מה־ReplayBuffer.
        
        Parameters:
        - policy_model: מודל ה־neural network הממפה state_vector → q_values.
        - replay_buffer: מופע של ReplayBuffer המכיל ניסיונות (state, action, reward, next_state).
        - device: 'cpu' או 'cuda'.
        - learning_rate: קצב הלמידה (α).
        - gamma: discount factor (γ) עבור חישוב TD-target.
        """
        self.policy_model = policy_model.to(device)
        self.replay_buffer = replay_buffer
        self.device = device
        self.gamma = gamma
        self.optimizer = optim.Adam(self.policy_model.parameters(), lr=learning_rate)
        self.loss_fn = nn.MSELoss()
        self.training_history = []
        self.target_model = copy.deepcopy(policy_model).to(device)
        self.target_model.eval()
        self.update_target_steps = 100  # כל כמה צעדים לעדכן
        self.train_step = 0

    def train_batch(self, batch_size):
        """
        מדגם batch מה־PrioritizedReplayBuffer ומעדכן את המודל לפי TD-learning (DQN).
        מחזיר את ערך האיבוד (loss) עבור האימון.
        """
        if self.replay_buffer.size() < batch_size:
            return None  # לא מספיק נתונים לאימון

        # מדגם חוויות בעדיפות (Prioritized Sampling)
        states, actions, rewards, next_states, dones, weights, indices = self.replay_buffer.sample_batch(batch_size)
        
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)
        weights = torch.tensor(weights, dtype=torch.float32).to(self.device)

        # חישוב Q-values עבור ה־states הנוכחיים:
        q_values = self.policy_model.forward(states)
        current_q_values = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)

        # חישוב Q-values עבור ה־next_states:
        next_q_values = self.target_model.forward(next_states)
        max_next_q_values = next_q_values.max(1)[0]
        dones = dones.float()
        td_target = rewards + self.gamma * max_next_q_values * (1 - dones)

        td_target = td_target.detach()

        # חישוב ה־TD error
        td_errors = torch.abs(current_q_values - td_target)

        # חישוב האיבוד על פי ה-weight של כל חוויה
        loss = (weights * td_errors).mean()

        # ביצוע backpropagation
        self.optimizer.zero_grad()
        loss.backward()

        self.train_step += 1
        if self.train_step % self.update_target_steps == 0:
            self.target_model.load_state_dict(self.policy_model.state_dict())

        self.optimizer.step()

        # עדכון ה-priorities
        self.replay_buffer.update_priorities(indices, td_errors.detach().cpu().numpy())

        return loss.item()

    def evaluate_action(self, state):
        """
        מקבל state (וקטור) ומחזיר את Q-values לכל הפעולות האפשריות.
        """
        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(self.device)
            q_values = self.policy_model.forward(state_tensor)
            return q_values.cpu().numpy()

    def save_model(self, path):
        """
        שומר את המודל לדיסק.
        """
        torch.save(self.policy_model.state_dict(), path)

    def load_model(self, path):
        """
        טוען את המודל מהדיסק.
        """
        self.policy_model.load_state_dict(torch.load(path, map_location=self.device))
        self.policy_model.eval()

    def plot_learning_curve(self):
        """
        מציג גרף של איבוד האימון לאורך זמן.
        """
        import matplotlib.pyplot as plt
        plt.plot(self.training_history)
        plt.xlabel("Training Iterations")
        plt.ylabel("Loss")
        plt.title("Learning Curve")
        plt.show()
