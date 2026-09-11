import pytest

from watchdog.config import ConfigError, parse_duration, parse_quiet_hours


@pytest.mark.parametrize(
    "raw,expected",
    [("30s", 30), ("15m", 900), ("6h", 21600), ("2d", 172800)],
)
def test_parse_duration(raw, expected):
    assert parse_duration(raw) == expected


@pytest.mark.parametrize("raw", ["", "6", "6x", "-1h", "0h", "h6"])
def test_bad_duration_fails_loudly(raw):
    with pytest.raises(ConfigError):
        parse_duration(raw)


def test_quiet_hours_parsed():
    start, end = parse_quiet_hours("23:00-08:00")
    assert (start.hour, end.hour) == (23, 8)


def test_quiet_hours_optional():
    assert parse_quiet_hours(None) is None


def test_bad_quiet_hours_fails():
    with pytest.raises(ConfigError):
        parse_quiet_hours("23-08")
