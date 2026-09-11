"""Отправка алертов в Telegram.

Без токена и chat_id сервис не падает, а переходит в режим журнала: сторож,
который не стартует из-за ненастроенных уведомлений, оставляет систему вообще
без присмотра.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

log = logging.getLogger("watchdog.notifier")


class Notifier:
    def __init__(self, chat_id: Optional[str], token: Optional[str] = None,
                 timeout: float = 10.0) -> None:
        self.chat_id = chat_id
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.chat_id and self.token)

    def send(self, text: str) -> bool:
        if not self.enabled:
            log.warning("уведомления выключены, алерт только в журнал: %s", text)
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            response = httpx.post(
                url,
                json={"chat_id": self.chat_id, "text": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            # Падение доставки алерта не должно ронять цикл проверки:
            # иначе один недоступный Telegram выключает наблюдение целиком.
            log.error("не удалось отправить алерт: %s", exc)
            return False
