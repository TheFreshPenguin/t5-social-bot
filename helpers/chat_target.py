from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ChatTarget:
    chat_id: int
    thread_id: Optional[int] = None

    @staticmethod
    def parse(raw: str) -> 'ChatTarget':
        tokens = [token for token in raw.strip().split('/') if token]
        if len(tokens) < 1:
            raise ValueError('Invalid chat target format')

        chat_id = int(tokens[0])
        thread_id = int(tokens[1]) if len(tokens) > 1 else None

        return ChatTarget(chat_id, thread_id)

    @staticmethod
    def parse_multi(raw: str) -> set['ChatTarget']:
        return {ChatTarget.parse(raw_single) for raw_single in raw.split(',') if raw_single}
