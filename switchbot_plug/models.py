"""Data models for SwitchBot Plug Mini."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PlugMiniData:
    """Parsed SwitchBot Plug Mini advertisement data.

    Attributes:
        mac: Device MAC address (e.g. '0C:4E:A0:36:08:46').
             Extracted from payload, ensuring consistent MAC even on macOS.
        sequence: Sequence number (1-255), increments when status updates.
        is_on: Relay power state (True: ON, False: OFF).
        power_w: Current active power consumption in Watts (0.1W resolution).
        overload: True if load exceeds limit (>15A).
        delay_flag: Bit0 of flags - Delay timer active.
        timer_flag: Bit1 of flags - Timer active.
        sync_utc_time_flag: Bit2 of flags - UTC time synchronized.
        wifi_rssi: Wi-Fi RSSI indicator value.
        ble_rssi: BLE signal RSSI in dBm (from advertising report), if available.
        raw_payload: Hex string or bytes of the parsed manufacturer payload.
        timestamp: Time when the packet was received/parsed.
    """

    mac: str
    sequence: int
    is_on: bool
    power_w: float
    overload: bool
    delay_flag: bool
    timer_flag: bool
    sync_utc_time_flag: bool
    wifi_rssi: int
    ble_rssi: Optional[int] = None
    raw_payload: Optional[bytes] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        state_str = "ON" if self.is_on else "OFF"
        overload_str = " OVERLOAD!" if self.overload else ""
        rssi_str = f" RSSI={self.ble_rssi}dBm" if self.ble_rssi is not None else ""
        time_str = self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        return (
            f"[{time_str}] [PLUG] MAC={self.mac}{rssi_str} "
            f"Power={self.power_w:5.1f}W State={state_str:<3} "
            f"Seq=0x{self.sequence:02X} Overload={int(self.overload)}{overload_str}"
        )
