from abc import ABC, abstractmethod
from typing import List

class BaseLLM(ABC):
    """
    Abstract base class for LLM interfaces.
    All language model implementations must inherit from this class and implement the following methods.
    """

    @abstractmethod
    def run(self, prompts: List[str]) -> List[str]:
        """
        Executes a list of prompts sequentially, preserving context.
        Returns a list of outputs.
        """
        raise NotImplementedError

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Counts the number of tokens in the given text.
        """
        raise NotImplementedError