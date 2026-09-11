from datetime import datetime, time

from watchdog.checker import Alert, evaluate, in_quiet_hours, recovered
from watchdog.config import Config, Source

HOUR = 3600


def cfg(*sources, repeat_after=12 * HOUR):
    return Config(sources=tuple(sources), telegram_chat_id=None, repeat_after=repeat_after)


def test_silent_source_produces_alert():
    config = cfg(Source("novofon", 72 * HOUR))
    now = 1_000_000
    alerts = evaluate(config, {"novofon": now - 80 * HOUR}, {}, now, now - 100 * HOUR)
    assert [a.source for a in alerts] == ["novofon"]
    assert alerts[0].first_time is False


def test_fresh_source_is_quiet():
    config = cfg(Source("novofon", 72 * HOUR))
    now = 1_000_000
    assert evaluate(config, {"novofon": now - HOUR}, {}, now, now - 100 * HOUR) == []


def test_source_that_never_reported_counts_from_start():
    """Интеграция, сломанная с самого начала, обязана дать алерт."""
    config = cfg(Source("avito", 6 * HOUR))
    now = 1_000_000
    alerts = evaluate(config, {}, {}, now, started_at=now - 10 * HOUR)
    assert len(alerts) == 1
    assert alerts[0].first_time is True


def test_repeat_alert_is_throttled():
    config = cfg(Source("novofon", 72 * HOUR), repeat_after=12 * HOUR)
    now = 1_000_000
    seen = {"novofon": now - 80 * HOUR}
    assert evaluate(config, seen, {"novofon": now - HOUR}, now, now) == []
    assert len(evaluate(config, seen, {"novofon": now - 13 * HOUR}, now, now)) == 1


def test_quiet_hours_suppress_alert_but_not_the_timer():
    config = cfg(Source("avito", 6 * HOUR, (time(23, 0), time(8, 0))))
    now = 1_000_000
    seen = {"avito": now - 10 * HOUR}
    night = datetime(2026, 9, 9, 2, 30)
    day = datetime(2026, 9, 9, 12, 0)
    assert evaluate(config, seen, {}, now, now, clock=night) == []
    assert len(evaluate(config, seen, {}, now, now, clock=day)) == 1


def test_quiet_window_across_midnight():
    window = (time(23, 0), time(8, 0))
    assert in_quiet_hours(datetime(2026, 9, 9, 23, 30), window) is True
    assert in_quiet_hours(datetime(2026, 9, 9, 7, 59), window) is True
    assert in_quiet_hours(datetime(2026, 9, 9, 8, 1), window) is False


def test_recovered_sources_are_detected():
    config = cfg(Source("novofon", 72 * HOUR))
    now = 1_000_000
    back = recovered(config, {"novofon": now - HOUR}, {"novofon": now - 2 * HOUR}, now)
    assert back == ["novofon"]


def test_alert_text_mentions_hours():
    alert = Alert("novofon", 80 * HOUR, 72 * HOUR, first_time=False)
    text = alert.text()
    assert "novofon" in text and "80.0" in text and "72.0" in text
