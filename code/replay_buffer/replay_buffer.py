###### Not using it now ######

import random

class ReplayBuffer:
    def __init__(self, max_size=10000):
        self.buffer = []
        self.max_size = max_size

    def add_experience(self, state, action, reward, next_state):
        """
        מוסיף ניסיון חדש למאגר הזיכרון.
        """
        experience = {
            "state": state,
            "action": action,
            "reward": reward,
            "next_state": next_state
        }
        if len(self.buffer) >= self.max_size:
            self.buffer.pop(0)  # FIFO – מוחק את הראשון
        self.buffer.append(experience)

    def sample_batch(self, batch_size):
        """
        מחזיר תת־קבוצה אקראית מהמאגר ללמידה.
        """
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def get_recent(self, n=5):
        """
        מחזיר את n הניסיונות האחרונים.
        """
        return self.buffer[-n:]

    def clear(self):
        """
        מאפס את הזיכרון לחלוטין.
        """
        self.buffer.clear()

    def size(self):
        return len(self.buffer)
