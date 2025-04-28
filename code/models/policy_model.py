import torch
import torch.nn as nn
import torch.nn.functional as F

class PolicyModel(nn.Module):
    """
    A fully-connected Q-network for reinforcement learning.
    Maps input state vectors to Q-values for each action.
    """

    def __init__(self, state_size, action_size, hidden_sizes=[512, 256, 128], learning_rate=1e-3, gamma=0.99):
        """
        Initialize the Q-network.

        Args:
            state_size (int): Size of the input state vector.
            action_size (int): Number of possible actions.
            hidden_sizes (list): List of hidden layer sizes (default: [512, 256, 128]).
            learning_rate (float): Learning rate for the optimizer.
            gamma (float): Discount factor for future rewards.
        """
        super(PolicyModel, self).__init__()

        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma

        # Dynamically build hidden layers
        layers = []
        input_dim = state_size
        for hidden_dim in hidden_sizes:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            input_dim = hidden_dim
        layers.append(nn.Linear(input_dim, action_size))

        self.network = nn.Sequential(*layers)

        self.loss_fn = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=learning_rate)

    def forward(self, state_vector):
        """
        Compute the Q-values for a given input state vector.

        Args:
            state_vector (Tensor or list): The input state representation.

        Returns:
            Tensor: Q-values for each possible action.
        """
        if not isinstance(state_vector, torch.Tensor):
            state_vector = torch.tensor(state_vector, dtype=torch.float32)

        if state_vector.ndim == 1:
            state_vector = state_vector.unsqueeze(0)  # Add batch dimension

        return self.network(state_vector)  # Raw Q-values

    def predict_best_action(self, state_vector):
        """
        Predict the index of the best action based on current Q-values.

        Args:
            state_vector (Tensor or list): Encoded state input.

        Returns:
            int: Index of action with the highest Q-value.
        """
        with torch.no_grad():
            q_values = self.forward(state_vector)
            return torch.argmax(q_values, dim=1).item()

    def update(self, experience):
        """
        Perform a single Q-learning update based on one experience tuple.

        Args:
            experience (dict): Contains 'state', 'action', 'reward', 'next_state'.

        Returns:
            tuple: (predicted_q_value, loss_value)
        """
        state = experience["state"]
        action = torch.tensor([experience["action"]], dtype=torch.long)
        reward = torch.tensor([experience["reward"]], dtype=torch.float32)
        next_state = experience["next_state"]

        if state.ndim == 1:
            state = state.unsqueeze(0)
        if next_state.ndim == 1:
            next_state = next_state.unsqueeze(0)

        # Q(s, a)
        q_values = self.forward(state)
        q_value = q_values.gather(1, action.unsqueeze(1)).squeeze(1)

        # max_a' Q(next_state, a')
        next_q_values = self.forward(next_state)
        max_next_q_value = next_q_values.max(1)[0].detach()

        # TD Target
        td_target = reward + self.gamma * max_next_q_value

        # Loss = MSE(Q, TD_target)
        loss = self.loss_fn(q_value, td_target)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return q_value.item(), loss.item()

    def save(self, path):
        """
        Save the model weights to disk.

        Args:
            path (str): Path to save the model.
        """
        torch.save(self.state_dict(), path)

    def load(self, path):
        """
        Load the model weights from disk.

        Args:
            path (str): Path to load model from.
        """
        self.load_state_dict(torch.load(path))
        self.eval()
