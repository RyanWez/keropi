"""Remembers Telegram file_ids for cards already sent.

Once a photo has been uploaded, Telegram will re-send it from just its file_id, so a
repeat number costs a dictionary lookup instead of ~30 ms of rendering plus a 17 KB
upload. In a shop the same customers come back, so most requests hit this.

Caching a KBZPay card is safe even though its payload embeds a timestamp: the
recorded behaviour is that an old timestamp keeps working, and the app's 30-second
refresh only re-renders the UI rather than asking the server for a new code.

Bounded and in-memory. It is lost on restart, which merely costs a re-render, and
Render's free tier restarts without warning anyway.
"""

import logging
from collections import OrderedDict

from bot import config
from bot.services.providers import Provider

logger = logging.getLogger(__name__)


class FileIdCache:
    def __init__(self, capacity: int) -> None:
        self.capacity = max(0, capacity)
        self._entries: OrderedDict[tuple[str, str, str], str] = OrderedDict()

    @staticmethod
    def _key(provider: Provider, phone: str, warning: str | None) -> tuple[str, str, str]:
        # The warning is drawn onto the image, so a card with one is a different card.
        return provider.value, phone, warning or ""

    def get(self, provider: Provider, phone: str, warning: str | None = None) -> str | None:
        key = self._key(provider, phone, warning)
        file_id = self._entries.get(key)
        if file_id is not None:
            self._entries.move_to_end(key)
        return file_id

    def put(
        self, provider: Provider, phone: str, file_id: str, warning: str | None = None
    ) -> None:
        if self.capacity == 0:
            return
        key = self._key(provider, phone, warning)
        self._entries[key] = file_id
        self._entries.move_to_end(key)
        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def discard(self, provider: Provider, phone: str, warning: str | None = None) -> None:
        """Forget an entry Telegram has stopped accepting."""
        self._entries.pop(self._key(provider, phone, warning), None)

    def __len__(self) -> int:
        return len(self._entries)


cache = FileIdCache(config.QR_CACHE_SIZE)
