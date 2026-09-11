from watchdog.store import Store


def test_heartbeat_roundtrip(tmp_path):
    store = Store(str(tmp_path / "w.db"))
    store.heartbeat("novofon", 1000)
    assert store.last_seen("novofon") == 1000
    store.heartbeat("novofon", 2000)
    assert store.last_seen("novofon") == 2000
    assert store.all_last_seen() == {"novofon": 2000}


def test_alerts_are_recorded_and_cleared(tmp_path):
    store = Store(str(tmp_path / "w.db"))
    assert store.alert_sent_at("novofon") is None
    store.record_alert("novofon", 1000, 90000)
    assert store.alert_sent_at("novofon") == 1000
    store.clear_alert("novofon")
    assert store.alert_sent_at("novofon") is None


def test_unknown_source_has_no_last_seen(tmp_path):
    store = Store(str(tmp_path / "w.db"))
    assert store.last_seen("нет-такого") is None
