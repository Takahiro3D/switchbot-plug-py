"""Unit tests for SwitchBot Plug Mini parser and data models."""

import json
import unittest
from datetime import datetime

from switchbot_plug.models import PlugMiniData
from switchbot_plug.parser import COMPANY_ID, parse_plug_mini_mfr_data
from switchbot_plug.scanner import normalize_mac
from switchbot_plug.cli import make_json_output


class TestSwitchBotPlugParser(unittest.TestCase):
    def test_company_id(self):
        """Check Bluetooth SIG Company ID for SwitchBot."""
        self.assertEqual(COMPANY_ID, 0x0969)

    def test_parse_14_byte_raw_ad(self):
        """Test parsing 14-byte raw manufacturer payload with 0x69 0x09 prefix."""
        # 0-1: 0x69 0x09 (Company ID 0x0969)
        # 2-7: 0C 4E A0 36 08 46 (MAC)
        # 8: 0x05 (Sequence: 5)
        # 9: 0x80 (ON)
        # 10: 0x03 (Flags: delay=True, timer=True, utc=False)
        # 11: 0x4B (WiFi RSSI: 75)
        # 12: 0x00 (Overload=0, Power MSB=0)
        # 13: 0x7B (Power LSB=123 -> 12.3W)
        raw_ad = bytes([
            0x69, 0x09,
            0x0C, 0x4E, 0xA0, 0x36, 0x08, 0x46,
            0x05,
            0x80,
            0x03,
            0x4B,
            0x00, 0x7B,
        ])
        result = parse_plug_mini_mfr_data(raw_ad, ble_rssi=-65)
        self.assertIsNotNone(result)
        assert result is not None

        self.assertEqual(result.mac, "0C:4E:A0:36:08:46")
        self.assertEqual(result.sequence, 5)
        self.assertTrue(result.is_on)
        self.assertEqual(result.power_w, 12.3)
        self.assertFalse(result.overload)
        self.assertTrue(result.delay_flag)
        self.assertTrue(result.timer_flag)
        self.assertFalse(result.sync_utc_time_flag)
        self.assertEqual(result.wifi_rssi, 75)
        self.assertEqual(result.ble_rssi, -65)
        self.assertIsInstance(result.timestamp, datetime)

    def test_parse_12_byte_bleak_format(self):
        """Test parsing 12-byte payload as returned by Bleak (Company ID omitted)."""
        # 0-5: MAC
        # 6: Seq 42
        # 7: 0x00 (OFF)
        # 8: 0x04 (UTC synced)
        # 9: 0x50 (WiFi RSSI)
        # 10: 0x81 (Overload=1, Power MSB=1)
        # 11: 0xF4 (Power LSB: (1 << 8) | 0xF4 = 500 -> 50.0W)
        payload = bytes([
            0x11, 0x22, 0x33, 0xAA, 0xBB, 0xCC,
            42,
            0x00,
            0x04,
            0x50,
            0x81, 0xF4,
        ])
        result = parse_plug_mini_mfr_data(payload, ble_rssi=-50)
        self.assertIsNotNone(result)
        assert result is not None

        self.assertEqual(result.mac, "11:22:33:AA:BB:CC")
        self.assertEqual(result.sequence, 42)
        self.assertFalse(result.is_on)
        self.assertEqual(result.power_w, 50.0)
        self.assertTrue(result.overload)
        self.assertFalse(result.delay_flag)
        self.assertFalse(result.timer_flag)
        self.assertTrue(result.sync_utc_time_flag)
        self.assertEqual(result.ble_rssi, -50)

    def test_invalid_lengths(self):
        """Test that invalid lengths return None."""
        self.assertIsNone(parse_plug_mini_mfr_data(b""))
        self.assertIsNone(parse_plug_mini_mfr_data(bytes([0x01] * 11)))
        self.assertIsNone(parse_plug_mini_mfr_data(bytes([0x69, 0x09] + [0x01] * 10)))

    def test_normalize_mac(self):
        """Test MAC normalization."""
        self.assertEqual(normalize_mac("0c:4e:a0:36:08:46"), "0C:4E:A0:36:08:46")
        self.assertEqual(normalize_mac("0C-4E-A0-36-08-46"), "0C:4E:A0:36:08:46")
        self.assertEqual(normalize_mac("0c4ea0360846"), "0C:4E:A0:36:08:46")

    def test_str_and_json(self):
        """Test string formatting and json output."""
        fixed_time = datetime(2026, 11, 24, 12, 30, 45, 123456)
        data = PlugMiniData(
            mac="0C:4E:A0:36:08:46",
            sequence=10,
            is_on=True,
            power_w=15.2,
            overload=False,
            delay_flag=False,
            timer_flag=False,
            sync_utc_time_flag=True,
            wifi_rssi=80,
            ble_rssi=-58,
            raw_payload=b"\x00\x01\x02",
            timestamp=fixed_time,
        )
        s = str(data)
        self.assertIn("12:30:45.123", s)
        self.assertIn("0C:4E:A0:36:08:46", s)
        self.assertIn("15.2W", s)
        self.assertIn("ON", s)
        self.assertIn("-58dBm", s)

        json_str = make_json_output(data)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["mac"], "0C:4E:A0:36:08:46")
        self.assertEqual(parsed["power_w"], 15.2)
        self.assertEqual(parsed["raw_payload"], "000102")
        self.assertEqual(parsed["timestamp"], "2026-11-24T12:30:45.123456")


if __name__ == "__main__":
    unittest.main()
