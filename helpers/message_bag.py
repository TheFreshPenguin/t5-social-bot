import random


class MessageBag:
    def __init__(self, messages: list[str]):
        self.messages: list[str] = messages

    @property
    def random(self) -> str:
        return random.choice(self.messages)
