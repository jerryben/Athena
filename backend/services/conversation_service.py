from backend.services.history_service import history_service


class ConversationService:

    def history(self):
        return history_service.messages()

    def last(self, n: int = 10):
        return history_service.last(n)

    def clear(self):
        history_service.clear()


conversation_service = ConversationService()