"""Tests for Scanner logic using mock BLE packets."""

import unittest
from unittest.mock import MagicMock

from switchbot_plug.scanner import SwitchBotPlugScanner, normalize_mac
from switchbot_plug.models import PlugMiniData


class TestScannerLogic(unittest.TestCase):
    def setUp(self):
        self.received = []
        self.callback = lambda data: self.received.append(data)

    def test_deduplication_by_sequence(self):
        """Test that same sequence number is deduplicated when deduplicate=True."""
        scanner = SwitchBotPlugScanner.__new__(SwitchBotPlugScanner)
        scanner.callback = self.callback
        scanner.target_mac = None
        scanner.deduplicate = True
        scanner.debug = False
        scanner._last_sequences = {}

        # Mock device and advertisement
        mock_device = MagicMock()
        mock_device.address = "E621E1F8-C36C-495A-93FC-0C247A3E6E5F"

        mock_adv = MagicMock()
        mock_adv.rssi = -60
        # 12 bytes payload: MAC 0C:4E:A0:36:08:46, Seq 1, ON, 12.0W
        payload = bytes([
            0x0C, 0x4E, 0xA0, 0x36, 0x08, 0x46,
            0x01,  # Seq 1
            0x80,
            0x00,
            0x50,
            0x00, 0x78,
        ])
        mock_adv.manufacturer_data = {0x0969: payload}

        # First advertisement -> should be processed
        scanner._handle_advertisement(mock_device, mock_adv)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0].sequence, 1)

        # Second advertisement with same sequence -> should be suppressed
        scanner._handle_advertisement(mock_device, mock_adv)
        self.assertEqual(len(self.received), 1)

        # Third advertisement with new sequence (Seq 2) -> should be processed
        payload2 = bytes([
            0x0C, 0x4E, 0xA0, 0x36, 0x08, 0x46,
            0x02,  # Seq 2
            0x80,
            0x00,
            0x50,
            0x00, 0x82,
        ])
        mock_adv.manufacturer_data = {0x0969: payload2}
        scanner._handle_advertisement(mock_device, mock_adv)
        self.assertEqual(len(self.received), 2)
        self.assertEqual(self.received[1].sequence, 2)

    def test_mac_filter(self):
        """Test filtering by target MAC address."""
        scanner = SwitchBotPlugScanner.__new__(SwitchBotPlugScanner)
        scanner.callback = self.callback
        scanner.target_mac = "0C:4E:A0:36:08:46"
        scanner.deduplicate = False
        scanner.debug = False
        scanner._last_sequences = {}

        mock_device = MagicMock()
        mock_device.address = "SOME-RANDOM-UUID"

        # Matching MAC payload
        mock_adv_match = MagicMock()
        mock_adv_match.rssi = -55
        mock_adv_match.manufacturer_data = {
            0x0969: bytes([0x0C, 0x4E, 0xA0, 0x36, 0x08, 0x46, 1, 0x80, 0, 50, 0, 100])
        }

        # Non-matching MAC payload
        mock_adv_other = MagicMock()
        mock_adv_other.rssi = -70
        mock_adv_other.manufacturer_data = {
            0x0969: bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 1, 0x80, 0, 50, 0, 100])
        }

        scanner._handle_advertisement(mock_device, mock_adv_other)
        self.assertEqual(len(self.received), 0)

        scanner._handle_advertisement(mock_device, mock_adv_match)
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0].mac, "0C:4E:A0:36:08:46")


if __name__ == "__main__":
    unittest.main()
