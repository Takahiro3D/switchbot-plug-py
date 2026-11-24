# SwitchBot Plug Mini BLE Scanner (Python)

[English](README.md) | [日本語](README_JP.md)

A cross-platform Python scanner for SwitchBot Plug Mini (JP / US) BLE advertisements.  
Passively monitors and parses real-time power consumption, relay state (ON/OFF), overload status, and Wi-Fi RSSI without pairing or cloud API dependencies.

---

## Features

- **Cross-Platform**:
  - Built on [`bleak`](https://github.com/hbldh/bleak), supporting macOS (CoreBluetooth), Linux (BlueZ), and Windows 10/11 (WinRT).
  - **macOS Real MAC Resolution**: While macOS typically hides device MAC addresses behind random UUIDs, this scanner extracts the physical MAC address directly from the manufacturer advertisement payload, ensuring uniform device identification across all platforms.
- **Connectionless (Passive Scan)**:
  - Listens to broadcast advertisements without establishing a BLE connection or pairing. Low power, high speed, and capable of monitoring multiple plugs simultaneously.
- **Deduplication**:
  - Tracks sequence numbers and outputs updates only when power or state changes occur. Can be disabled with `-a` / `--all` to view all incoming packets.
- **Timestamping with Millisecond Precision**:
  - Displays reception timestamps with millisecond resolution (`[HH:MM:SS.mmm]`), making telemetry update intervals easy to observe.
- **Overload & Wi-Fi Telemetry**:
  - Detects overload flags (>15A) and captures the plug's internal Wi-Fi RSSI.
- **CLI & Module Usage**:
  - Ready-to-run command-line tool with text and JSON outputs, plus an importable library for custom Python integrations.

---

## Extracted Telemetry

| Field | Type / Unit | Description |
| :--- | :--- | :--- |
| **Timestamp** | `datetime` | Packet reception timestamp (millisecond resolution) |
| **MAC Address** | `str` (XX:XX:XX:XX:XX:XX) | Physical MAC address of the plug (Big-endian) |
| **Power** | `float` (Watts) | Active power consumption (0.1W resolution) |
| **State** | `bool` (ON / OFF) | Relay power output state |
| **Sequence** | `int` (1 - 255) | Increments each time internal data updates (~5s interval) |
| **Overload** | `bool` | Current limit exceeded flag (>15A) |
| **Flags** | `bool` | Delay timer, scheduled timer, and UTC time synchronization |
| **Wi-Fi RSSI** | `int` | Wi-Fi signal strength received by the plug |
| **BLE RSSI** | `int` (dBm) | BLE signal strength measured by the scanner host |

---

## Installation & Setup

```bash
cd switchbot-plug-py

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Basic Scan (Monitor all nearby Plug Minis)

```bash
python main.py
```
or
```bash
python -m switchbot_plug.cli
```

**Output Example**:
```text
=== SwitchBot Plug Mini BLE Scanner (Python) ===
Filter MAC : None (monitoring all Plug Minis)
Deduplicate: ON (changes only)
Mode       : Text output
Timeout    : Indefinite (Press Ctrl+C to stop)
------------------------------------------------
[12:28:30.123] [PLUG] MAC=0C:4E:A0:36:08:46 RSSI=-55dBm Power= 12.3W State=ON  Seq=0x01 Overload=0
[12:28:35.240] [PLUG] MAC=0C:4E:A0:36:08:46 RSSI=-56dBm Power= 12.8W State=ON  Seq=0x02 Overload=0
```

### CLI Options

```text
usage: switchbot-plug [-h] [-m MAC] [-a] [-d] [-j] [-t TIMEOUT]

SwitchBot Plug Mini BLE Advertisement Scanner (Cross-platform Python)

options:
  -h, --help            show this help message and exit
  -m, --mac MAC         Target MAC address to filter (e.g. 0C:4E:A0:36:08:46).
  -a, --all             Disable deduplication; show every received advertisement packet.
  -d, --debug           Enable debug logs and hex dump of raw advertisement payload.
  -j, --json            Output data as newline-delimited JSON objects.
  -t, --timeout TIMEOUT Scan timeout in seconds (0 = continuous until Ctrl+C).
```

#### Filter by Specific MAC Address
```bash
python main.py -m 0C:4E:A0:36:08:46
```

#### Debug Mode (Show raw payload hex dump)
```bash
python main.py -d
```

#### Disable Deduplication (Show all incoming packets)
```bash
python main.py -a
```

#### JSON Output (For logging or external pipelines)
```bash
python main.py -j
```
Output Example:
```json
{"mac": "0C:4E:A0:36:08:46", "sequence": 1, "is_on": true, "power_w": 12.3, "overload": false, "delay_flag": false, "timer_flag": false, "sync_utc_time_flag": true, "wifi_rssi": 80, "ble_rssi": -55, "raw_payload": "0c4ea036084601800450007b", "timestamp": "2026-11-24T12:28:30.123456"}
```

---

## Library Usage in Python

```python
import asyncio
from switchbot_plug.scanner import SwitchBotPlugScanner
from switchbot_plug.models import PlugMiniData

def handle_data(data: PlugMiniData):
    print(f"[{data.timestamp}] {data.mac}: {data.power_w} W, State={'ON' if data.is_on else 'OFF'}")

async def main():
    scanner = SwitchBotPlugScanner(
        callback=handle_data,
        target_mac="0C:4E:A0:36:08:46",  # Optional: filter by MAC
        deduplicate=True,                 # Notify only on sequence number change
    )
    # Scan for 30 seconds (0 or omitted means run until stopped)
    await scanner.scan(timeout=30)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Platform-Specific Notes

- **macOS**:
  - On the first run, macOS may prompt for Bluetooth permission for your terminal app (Terminal.app, iTerm2, VSCode, etc.). Click **Allow**.
- **Linux (Raspberry Pi, Ubuntu, etc.)**:
  - BlueZ is required (`sudo apt install bluez`).
  - BLE scanning requires raw socket capabilities. Grant permissions with:
    ```bash
    sudo setcap cap_net_raw,cap_net_admin+eip $(which python3)
    ```
    or add your user to the `bluetooth` group.
- **Windows**:
  - Works out of the box using Windows 10/11 Bluetooth APIs (WinRT).

---

## Running Tests

Unit tests run completely offline without BLE hardware:

```bash
python3 -m unittest discover -s tests -v
```
