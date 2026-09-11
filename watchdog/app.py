"""HTTP-интерфейс сторожа.

Источники сами сообщают о жизни: POST /heartbeat/{source}. Это дешевле, чем
опрашивать чужие системы, и работает даже там, где у интеграции нет API.
"""
from __future__ import annotations

import os
import threading
import time as time_module
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response

from .checker import evaluate, recovered
from .config import load
from .notifier import Notifier
from .store import Store

CONFIG_PATH = os.environ.get("WATCHDOG_CONFIG", "config.yaml")
DB_PATH = os.environ.get("WATCHDOG_DB", "data/watchdog.db")
CHECK_INTERVAL = int(os.environ.get("WATCHDOG_INTERVAL", "60"))

state: dict = {}


def run_check() -> list[str]:
    config = state["config"]
    store: Store = state["store"]
    notifier: Notifier = state["notifier"]
    now = int(time_module.time())

    last_seen = store.all_last_seen()
    alerts_sent = {
        source.name: sent
        for source in config.sources
        if (sent := store.alert_sent_at(source.name)) is not None
    }

    for name in recovered(config, last_seen, alerts_sent, now):
        store.clear_alert(name)
        notifier.send(f"Источник «{name}» снова присылает события.")

    fired = []
    for alert in evaluate(config, last_seen, alerts_sent, now, state["started_at"]):
        notifier.send(alert.text())
        store.record_alert(alert.source, now, alert.silent_for)
        fired.append(alert.source)
    return fired


def _loop(stop: threading.Event) -> None:
    while not stop.wait(CHECK_INTERVAL):
        try:
            run_check()
        except Exception:  # цикл наблюдения не имеет права умереть
            import logging
            logging.getLogger("watchdog").exception("сбой цикла проверки")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    state["config"] = load(CONFIG_PATH)
    state["store"] = Store(DB_PATH)
    state["notifier"] = Notifier(state["config"].telegram_chat_id)
    state["started_at"] = int(time_module.time())
    stop = threading.Event()
    thread = threading.Thread(target=_loop, args=(stop,), daemon=True)
    thread.start()
    yield
    stop.set()


app = FastAPI(title="silence-watchdog", lifespan=lifespan)


@app.post("/heartbeat/{source}", status_code=204)
def heartbeat(source: str) -> Response:
    if state["config"].source(source) is None:
        raise HTTPException(404, f"источник {source!r} не объявлен в конфигурации")
    state["store"].heartbeat(source, int(time_module.time()))
    return Response(status_code=204)


@app.get("/status")
def status() -> dict:
    config = state["config"]
    store: Store = state["store"]
    now = int(time_module.time())
    last_seen = store.all_last_seen()
    items = []
    for source in config.sources:
        seen = last_seen.get(source.name)
        silent_for = now - (seen if seen is not None else state["started_at"])
        items.append(
            {
                "source": source.name,
                "last_seen": seen,
                "silent_for": silent_for,
                "max_silence": source.max_silence,
                "silent": silent_for >= source.max_silence,
            }
        )
    return {"now": now, "sources": items, "notifications": state["notifier"].enabled}


@app.get("/health")
def health() -> dict:
    return {"ok": True}
