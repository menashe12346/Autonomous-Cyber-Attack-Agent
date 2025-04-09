import torch
import torch.nn as nn
import torch.nn.functional as F

class PolicyModel(nn.Module):
    def __init__(self, state_size, action_size, hidden_sizes=[128, 64], learning_rate=1e-3, gamma=0.99):
        super(PolicyModel, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_sizes[0])
        self.fc2 = nn.Linear(hidden_sizes[0], hidden_sizes[1])
        self.output = nn.Linear(hidden_sizes[1], action_size)

        self.optimizer = torch.optim.Adam(self.parameters(), lr=learning_rate)
        self.loss_fn = nn.MSELoss()
        self.gamma = gamma  # discount factor

    def forward(self, state_vector):
        """
        מקבל state_vector ומחזיר Q-values לכל פעולה.
        """
        if not isinstance(state_vector, torch.Tensor):
            state_vector = torch.tensor(state_vector, dtype=torch.float32)

        if state_vector.ndim == 1:
            state_vector = state_vector.unsqueeze(0)  # הוספת מימד Batch

        x = F.relu(self.fc1(state_vector))
        x = F.relu(self.fc2(x))
        return self.output(x)  # No softmax – Q-values ממשיים

    def predict_best_action(self, state_vector):
        """
        מחזיר את אינדקס הפעולה עם Q-value הגבוה ביותר.
        """
        with torch.no_grad():
            q_values = self.forward(state_vector)
            return torch.argmax(q_values).item()

    def update(self, experience):
        """
        מעדכן את הרשת על בסיס ניסיון בודד (state, action, reward, next_state).
        """
        state = experience["state"].clone().detach().unsqueeze(0)
        action = torch.tensor([experience["action"]], dtype=torch.long)
        reward = torch.tensor([experience["reward"]], dtype=torch.float32)
        next_state = experience["next_state"].clone().detach().unsqueeze(0)

        # חישוב Q(s, a)
        q_values = self.forward(state)
        q_value = q_values.gather(1, action.unsqueeze(1)).squeeze(1)  # שומר על [batch]

        # חישוב max_a' Q(next_state, a')
        next_q_values = self.forward(next_state)
        max_next_q_value = next_q_values.max(1)[0].detach()

        # TD Target
        td_target = reward + self.gamma * max_next_q_value
        td_target = td_target.view(-1)

        # Loss = MSE(Q, TD_target)
        loss = self.loss_fn(q_value, td_target)

        # שלב האימון
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return q_value.item(), loss.item()

    def save(self, path):
        torch.save(self.state_dict(), path)

    def load(self, path):
        self.load_state_dict(torch.load(path))
        self.eval()
