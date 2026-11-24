"""BLE Scanner for SwitchBot Plug Mini using Bleak."""

import asyncio
import logging
from typing import Callable, Dict, Optional

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
except ImportError:
    BleakScanner = None
    BLEDevice = None
    AdvertisementData = None

from .models import PlugMiniData
from .parser import COMPANY_ID, parse_plug_mini_mfr_data

logger = logging.getLogger(__name__)


def normalize_mac(mac: str) -> str:
    """Normalize MAC address string to upper case colon-delimited format."""
    clean = mac.replace(":", "").replace("-", "").upper()
    if len(clean) == 12:
        return ":".join(clean[i : i + 2] for i in range(0, 12, 2))
    return mac.upper()


class SwitchBotPlugScanner:
    """Scanner for SwitchBot Plug Mini advertisements."""

    def __init__(
        self,
        callback: Callable[[PlugMiniData], None],
        target_mac: Optional[str] = None,
        deduplicate: bool = True,
        debug: bool = False,
    ):
        """Initialize SwitchBot Plug Scanner.

        Args:
            callback: Function called when a matching Plug Mini advertisement is received.
            target_mac: Optional MAC address to filter by (e.g. '0C:4E:A0:36:08:46').
            deduplicate: If True, suppress consecutive packets with unchanged sequence number.
            debug: If True, log verbose advertisement details.
        """
        if BleakScanner is None:
            raise ImportError(
                "The 'bleak' library is required for BLE scanning. "
                "Install it with: pip install bleak"
            )

        self.callback = callback
        self.target_mac = normalize_mac(target_mac) if target_mac else None
        self.deduplicate = deduplicate
        self.debug = debug
        self._last_sequences: Dict[str, int] = {}
        self._scanner: Optional[BleakScanner] = None

    def _handle_advertisement(
        self, device: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        """Bleak advertisement detection callback."""
        # Check manufacturer data for SwitchBot Company ID (0x0969)
        mfr_data = advertisement_data.manufacturer_data.get(COMPANY_ID)
        if not mfr_data:
            return

        if self.debug:
            logger.debug(
                "Found Company ID 0x%04X on device %s (RSSI=%d, len=%d): %s",
                COMPANY_ID,
                device.address,
                advertisement_data.rssi,
                len(mfr_data),
                mfr_data.hex(),
            )

        plug_data = parse_plug_mini_mfr_data(
            mfr_data, ble_rssi=advertisement_data.rssi
        )
        if not plug_data:
            return

        # Check MAC filter against both payload MAC and device address (for cross-platform)
        if self.target_mac:
            normalized_payload_mac = normalize_mac(plug_data.mac)
            normalized_dev_addr = normalize_mac(device.address)
            if (
                normalized_payload_mac != self.target_mac
                and normalized_dev_addr != self.target_mac
            ):
                return

        # Deduplication check by sequence number (per MAC)
        if self.deduplicate:
            last_seq = self._last_sequences.get(plug_data.mac)
            if last_seq == plug_data.sequence:
                return
            self._last_sequences[plug_data.mac] = plug_data.sequence

        self.callback(plug_data)

    async def scan(self, timeout: Optional[float] = None) -> None:
        """Start passive BLE scan.

        Args:
            timeout: Scan duration in seconds. None or 0 means scan indefinitely.
        """
        self._scanner = BleakScanner(
            detection_callback=self._handle_advertisement
        )

        logger.info("Starting SwitchBot Plug BLE scan...")
        await self._scanner.start()
        try:
            if timeout and timeout > 0:
                await asyncio.sleep(timeout)
            else:
                while True:
                    await asyncio.sleep(3600)
        finally:
            await self._scanner.stop()
            logger.info("BLE scan stopped.")
