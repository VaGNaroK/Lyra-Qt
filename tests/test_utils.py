import pytest
from core.utils import normalize_bitrate

def test_normalize_bitrate_empty():
    assert normalize_bitrate("") == "default"
    assert normalize_bitrate("   ") == "default"
    assert normalize_bitrate(None) == "default"

def test_normalize_bitrate_kbps():
    assert normalize_bitrate("320 kbps") == "320k"
    assert normalize_bitrate("128 Kbps") == "128k"

def test_normalize_bitrate_mbps():
    assert normalize_bitrate("2 mbps") == "2m"
    assert normalize_bitrate("5 Mbps") == "5m"

def test_normalize_bitrate_raw_number():
    assert normalize_bitrate("192") == "192k"
    assert normalize_bitrate("4000") == "4000k"

def test_normalize_bitrate_already_formatted():
    assert normalize_bitrate("320k") == "320k"
    assert normalize_bitrate("2m") == "2m"
