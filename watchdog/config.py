"""Загрузка и валидация конфигурации.

Ошибки конфигурации ловим на старте, а не в момент проверки: сторож, который
сам молча упал из-за опечатки в yaml, хуже, чем его отсутствие.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import time
from typing import Optional

import yaml

_DURATION = re.compile(r"^(\d+)(s|m|h|d)$")
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_QUIET = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")


class ConfigError(ValueError):
    pass


def parse_duration(raw: str) -> int:
    """'72h' -> 259200. Секунды, потому что дальше всё считается в них."""
    match = _DURATION.match(str(raw).strip())
    if not match:
        raise ConfigError(f"нечитаемая длительность: {raw!r}, ожидается вид 30m, 6h, 2d")
    value, unit = match.groups()
    seconds = int(value) * _UNITS[unit]
    if seconds <= 0:
        raise ConfigError(f"длительность должна быть больше нуля: {raw!r}")
    return seconds


def parse_quiet_hours(raw: Optional[str]) -> Optional[tuple[time, time]]:
    if raw in (None, "", "null"):
        return None
    match = _QUIET.match(str(raw).strip())
    if not match:
        raise ConfigError(f"нечитаемое окно тишины: {raw!r}, ожидается вид 23:00-08:00")
    h1, m1, h2, m2 = (int(x) for x in match.groups())
    try:
        return time(h1, m1), time(h2, m2)
    except ValueError as exc:
        raise ConfigError(f"нечитаемое окно тишины: {raw!r}") from exc


@dataclass(frozen=True)
class Source:
    name: str
    max_silence: int
    quiet_hours: Optional[tuple[time, time]] = None


@dataclass(frozen=True)
class Config:
    sources: tuple[Source, ...]
    telegram_chat_id: Optional[str]
    repeat_after: int

    def source(self, name: str) -> Optional[Source]:
        for item in self.sources:
            if item.name == name:
                return item
        return None


def _expand_env(value):
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1])
    return value


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    raw_sources = raw.get("sources") or []
    if not raw_sources:
        raise ConfigError("в конфигурации нет ни одного источника")

    names = set()
    sources = []
    for item in raw_sources:
        name = str(item.get("name") or "").strip()
        if not name:
            raise ConfigError("у источника нет имени")
        if name in names:
            raise ConfigError(f"источник {name!r} объявлен дважды")
        names.add(name)
        sources.append(
            Source(
                name=name,
                max_silence=parse_duration(item.get("max_silence")),
                quiet_hours=parse_quiet_hours(item.get("quiet_hours")),
            )
        )

    notify = raw.get("notify") or {}
    return Config(
        sources=tuple(sources),
        telegram_chat_id=_expand_env(notify.get("telegram_chat_id")),
        repeat_after=parse_duration(notify.get("repeat_after", "12h")),
    )
