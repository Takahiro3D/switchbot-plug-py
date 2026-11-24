"""Parser for SwitchBot Plug Mini BLE Advertisement packets.

References:
- SwitchBotAPI-BLE Official Specs:
  https://github.com/OpenWonderLabs/SwitchBotAPI-BLE
"""

from datetime import datetime
from typing import Optional
from .models import PlugMiniData

# Bluetooth SIG Company ID for Woan Technology (Shenzhen) Co., Ltd. (SwitchBot)
COMPANY_ID = 0x0969


def parse_plug_mini_mfr_data(
    data: bytes,
    ble_rssi: Optional[int] = None,
    timestamp: Optional[datetime] = None,
) -> Optional[PlugMiniData]:
    """Parse Manufacturer Specific Data payload from SwitchBot Plug Mini.

    Supports both formats:
    1. Raw AD payload including 2-byte Company ID (14 bytes total):
       - Byte 0-1: Company ID (0x69, 0x09 -> 0x0969 little-endian in BLE AD)
       - Byte 2-7: MAC Address (6 bytes, Big-endian)
       - Byte 8  : Sequence number (1-255)
       - Byte 9  : Plug state (bit7: 1=ON (0x80), 0=OFF (0x00))
       - Byte 10 : Flags (bit0: delay, bit1: timer, bit2: syncUtcTime)
       - Byte 11 : Wi-Fi RSSI
       - Byte 12 : Power MSB (bit7: overload flag, bit6-0: power msb)
       - Byte 13 : Power LSB

    2. Bleak manufacturer_data payload where Company ID 0x0969 is key and
       data is 12 bytes:
       - Byte 0-5: MAC Address (6 bytes, Big-endian)
       - Byte 6  : Sequence number (1-255)
       - Byte 7  : Plug state
       - Byte 8  : Flags
       - Byte 9  : Wi-Fi RSSI
       - Byte 10 : Power MSB
       - Byte 11 : Power LSB

    Args:
        data: Manufacturer payload bytes.
        ble_rssi: Optional BLE RSSI value in dBm.
        timestamp: Optional datetime when received.

    Returns:
        PlugMiniData if valid SwitchBot Plug Mini payload, otherwise None.
    """
    if not data:
        return None

    # Handle raw BLE AD payload with Company ID prefix (0x69, 0x09)
    if data.startswith(b"\x69\x09"):
        payload = data[2:]
    else:
        payload = data

    if len(payload) < 12:
        return None

    # Extract MAC address (Big-endian, 6 bytes)
    mac = ":".join(f"{b:02X}" for b in payload[0:6])

    # Sequence number
    sequence = payload[6]

    # Device state (0x00: OFF, 0x80: ON; bit7 is state)
    state_byte = payload[7]
    is_on = bool(state_byte & 0x80)

    # Status flags
    flags = payload[8]
    delay_flag = bool(flags & 0x01)
    timer_flag = bool(flags & 0x02)
    sync_utc_time_flag = bool(flags & 0x04)

    # Wi-Fi RSSI
    wifi_rssi = payload[9]

    # Power & Overload
    p_high = payload[10]
    p_low = payload[11]

    overload = bool(p_high & 0x80)
    power_raw = ((p_high & 0x7F) << 8) | p_low
    power_w = round(power_raw / 10.0, 1)

    kwargs = {
        "mac": mac,
        "sequence": sequence,
        "is_on": is_on,
        "power_w": power_w,
        "overload": overload,
        "delay_flag": delay_flag,
        "timer_flag": timer_flag,
        "sync_utc_time_flag": sync_utc_time_flag,
        "wifi_rssi": wifi_rssi,
        "ble_rssi": ble_rssi,
        "raw_payload": data,
    }
    if timestamp is not None:
        kwargs["timestamp"] = timestamp

    return PlugMiniData(**kwargs)
