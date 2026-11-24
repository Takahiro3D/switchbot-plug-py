# SwitchBot Plug Mini BLE Scanner (Python)

[English](README.md) | [日本語](README_JP.md)

SwitchBot プラグミニ（JP/US）のアドバタイズパケット（BLE Advertisement）を受信し、消費電力やリレー状態（ON/OFF）などをリアルタイムにパース・取得するPythonプログラムです。
macOS, Linux, Windows などのマルチプラットフォームで動作するように実装されています。

---

## 特長

- **マルチプラットフォーム対応**:
  - `bleak` ライブラリを採用し、Windows (WinRT), macOS (CoreBluetooth), Linux (BlueZ) で動作。
  - macOS では OS 仕様によりデバイスアドレスがランダムな UUID になりますが、本プログラムではアドバタイズパケット内の Manufacturer Data に含まれる実 MAC アドレスを抽出・正規化して表示・フィルタリングします。
- **コネクションレス（パッシブスキャン）**:
  - デバイスと BLE ペアリング・接続を行わず、周期的にブロードキャストされるアドバタイズを受信・解析するため、高速かつ低負荷で複数台のモニタリングが可能です。
- **重複排除機能**:
  - シーケンス番号（Sequence Number）を追跡し、電力や状態の変化があったパケットのみを出力可能（`-a` で全パケット表示も可能）。
- **取得時刻（ミリ秒精度）の表示**:
  - 受信パケットの時刻をミリ秒精度で表示し、データ更新周期を容易にモニタリング可能。
- **過負荷検出 & Wi-Fi RSSI 取得**:
  - 15A超の過負荷（Overload）フラグや、プラグ本体の Wi-Fi 電波強度も解析して取得します。
- **CLI & モジュール利用**:
  - コマンドラインツールとして即時実行できるほか、他の Python プログラムからライブラリとしてもインポートして利用可能です。

---

## 取得可能な情報

| 項目 | 型 / 単位 | 説明 |
| :--- | :--- | :--- |
| **Timestamp** | `datetime` | 受信時刻（ミリ秒精度） |
| **MAC Address** | 文字列 (XX:XX:XX:XX:XX:XX) | プラグ本体の実 MAC アドレス (Big-endian) |
| **Power** | `float` (W) | 現在の有効消費電力 (0.1W 刻み) |
| **State** | `bool` (ON / OFF) | リレーの通電状態 |
| **Sequence** | `int` (1~255) | 状態更新ごとにインクリメントされるシーケンス番号 |
| **Overload** | `bool` | 許容電流（15A等）超過フラグ |
| **Flags** | `bool` | ディレイタイマー、通常タイマー、UTC時刻同期フラグ |
| **Wi-Fi RSSI** | `int` | プラグ本体が受信している Wi-Fi 信号強度 |
| **BLE RSSI** | `int` (dBm) | スキャン端末側の BLE 受信電波強度 |

---

## インストール & セットアップ

### 仮想環境の作成とライブラリ導入

```bash
cd switchbot-plug-py

# 仮想環境作成
python3 -m venv .venv
source .venv/bin/activate  # Windows の場合は .venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

---

## 使い方

### 基本的な実行（周囲の全プラグミニをスキャン）

```bash
python main.py
```
または
```bash
python -m switchbot_plug.cli
```

出力例:
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

### オプション一覧

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

#### 例1: 特定の MAC アドレスのみフィルタリング
```bash
python main.py -m 0C:4E:A0:36:08:46
```

#### 例2: デバッグモード（RAW パケットの Hex ダンプ表示）
```bash
python main.py -d
```

#### 例3: 重複排除を無効化（全パケット表示）
```bash
python main.py -a
```

#### 例4: JSON 形式で出力（外部スクリプト連携・ログ保存用）
```bash
python main.py -j
```
出力例:
```json
{"mac": "0C:4E:A0:36:08:46", "sequence": 1, "is_on": true, "power_w": 12.3, "overload": false, "delay_flag": false, "timer_flag": false, "sync_utc_time_flag": true, "wifi_rssi": 80, "ble_rssi": -55, "raw_payload": "0c4ea036084601800450007b", "timestamp": "2026-11-24T12:28:30.123456"}
```

---

## Python コードからのライブラリ利用

```python
import asyncio
from switchbot_plug.scanner import SwitchBotPlugScanner
from switchbot_plug.models import PlugMiniData

def on_data_received(data: PlugMiniData):
    print(f"[{data.timestamp}] {data.mac}: {data.power_w} W, State={'ON' if data.is_on else 'OFF'}")

async def main():
    scanner = SwitchBotPlugScanner(
        callback=on_data_received,
        target_mac="0C:4E:A0:36:08:46",  # 省略時は全デバイス
        deduplicate=True,                 # シーケンス番号変更時のみ通知
    )
    # 30秒間スキャン (0 または指定なしで継続)
    await scanner.scan(timeout=30)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 各 OS での注意点

- **macOS**:
  - 初回実行時、ターミナル（Terminal.app / iTerm / VSCode 等）に「Bluetooth の使用を許可しますか？」というプロンプトが表示される場合があります。「許可」を選択してください。
- **Linux (Raspberry Pi / Ubuntu 等)**:
  - BlueZ が必要です（`sudo apt install bluez`）。
  - BLE スキャンには通常権限が必要なため、`sudo setcap cap_net_raw,cap_net_admin+eip $(which python3)` を実行するか、ユーザーを `bluetooth` グループに追加してください。
- **Windows**:
  - Windows 10/11 の標準 Bluetooth スタック (WinRT) で追加設定なしに動作します。

---

## テスト実行

```bash
python3 -m unittest discover -s tests -v
```
