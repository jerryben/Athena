from collections import deque


class HistoryService:

    def __init__(self):
        self.history = deque(maxlen=20)

    def add(self, role: str, content: str):
        self.history.append(
            {
                "role": role,
                "content": content
            }
        )

    def messages(self):
        return list(self.history)

    def last(self, n: int = 5):
        return list(self.history)[-n:]

    def clear(self):
        self.history.clear()


history_service = HistoryService()