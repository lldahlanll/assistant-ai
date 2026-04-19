from collections import defaultdict
from config.settings import settings


class ConversationHistory:
    """
    Simpan riwayat chat per user_id di memori.
    Format tiap pesan: {"role": "user"|"assistant", "content": "..."}

    Untuk upgrade ke Redis: ganti _store di sini saja,
    interface add/get/clear/count tidak berubah.
    """

    def __init__(self) -> None:
        self._store: dict[int, list[dict]] = defaultdict(list)

    def add(self, user_id: int, role: str, content: str) -> None:
        history = self._store[user_id]
        history.append({"role": role, "content": content})
        # Trim jika melebihi batas maksimum
        max_len = settings.max_history_length
        if len(history) > max_len:
            self._store[user_id] = history[-max_len:]

    def get(self, user_id: int) -> list[dict]:
        return list(self._store[user_id])

    def clear(self, user_id: int) -> None:
        self._store[user_id] = []

    def count(self, user_id: int) -> int:
        return len(self._store[user_id])


# Singleton — import conversation_history di mana saja
conversation_history = ConversationHistory()