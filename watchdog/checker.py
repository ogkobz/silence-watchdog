"""Ядро: решает, кто молчит дольше положенного.

Три правила, каждое из них выучено на живых граблях:

1. Источник, от которого не было ни одного события, считается молчащим с момента
   старта сторожа, а не «ещё не было данных». Иначе сломанная с самого начала
   интеграция не даст алерта никогда.
2. Пока идёт окно тишины (ночь), алерт не шлём, но и таймер не обнуляем.
3. Повторный алерт по тому же источнику — не чаще repeat_after. Сторож, который
   пишет каждую минуту, отключается человеком на второй день.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

from .config import Config, Source


@dataclass(frozen=True)
class Alert:
    source: str
    silent_for: int
    max_silence: int
    first_time: bool

    def text(self) -> str:
        hours = self.silent_for / 3600
        limit = self.max_silence / 3600
        head = "молчит" if not self.first_time else "не присылал событий ни разу"
        return (
            f"Источник «{self.source}» {head}: {hours:.1f} ч "
            f"при допустимых {limit:.1f} ч."
        )


def in_quiet_hours(moment: datetime, window: Optional[tuple[time, time]]) -> bool:
    if window is None:
        return False
    start, end = window
    now = moment.time()
    if start <= end:
        return start <= now < end
    # Окно через полночь: 23:00-08:00.
    return now >= start or now < end


def evaluate(
    config: Config,
    last_seen: dict[str, int],
    alerts_sent: dict[str, int],
    now: int,
    started_at: int,
    clock: Optional[datetime] = None,
) -> list[Alert]:
    moment = clock or datetime.fromtimestamp(now)
    result: list[Alert] = []

    for source in config.sources:
        if in_quiet_hours(moment, source.quiet_hours):
            continue

        seen = last_seen.get(source.name)
        first_time = seen is None
        reference = seen if seen is not None else started_at
        silent_for = now - reference
        if silent_for < source.max_silence:
            continue

        sent_at = alerts_sent.get(source.name)
        if sent_at is not None and now - sent_at < config.repeat_after:
            continue

        result.append(
            Alert(
                source=source.name,
                silent_for=silent_for,
                max_silence=source.max_silence,
                first_time=first_time,
            )
        )
    return result


def recovered(config: Config, last_seen: dict[str, int], alerts_sent: dict[str, int],
              now: int) -> list[str]:
    """Источники, которые снова заговорили — по ним алерт надо снять."""
    back: list[str] = []
    for name in alerts_sent:
        source: Optional[Source] = config.source(name)
        if source is None:
            back.append(name)
            continue
        seen = last_seen.get(name)
        if seen is not None and now - seen < source.max_silence:
            back.append(name)
    return back
