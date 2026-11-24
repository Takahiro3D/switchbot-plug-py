"""Command-line interface for SwitchBot Plug Mini BLE Scanner."""

import argparse
import asyncio
import dataclasses
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from .models import PlugMiniData
from .scanner import SwitchBotPlugScanner


def make_json_output(data: PlugMiniData) -> str:
    """Format PlugMiniData as a JSON string."""
    d = dataclasses.asdict(data)
    if d.get("raw_payload"):
        d["raw_payload"] = d["raw_payload"].hex()
    if isinstance(d.get("timestamp"), datetime):
        d["timestamp"] = d["timestamp"].isoformat()
    return json.dumps(d, ensure_ascii=False)


def handle_packet(data: PlugMiniData, output_json: bool, debug: bool) -> None:
    """Print parsed packet according to user flags."""
    if output_json:
        print(make_json_output(data), flush=True)
        return

    # Plain text format matching the C output style with timestamp
    print(str(data), flush=True)
    if debug and data.raw_payload:
        print(f"  [RAW] {data.raw_payload.hex(' ')}", flush=True)


async def async_main(args: argparse.Namespace) -> None:
    """Async main routine."""
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format="[%(levelname)s] %(message)s",
        level=level,
    )

    print("=== SwitchBot Plug Mini BLE Scanner (Python) ===")
    if args.mac:
        print(f"Filter MAC : {args.mac.upper()}")
    else:
        print("Filter MAC : None (monitoring all Plug Minis)")
    print(f"Deduplicate: {'ON (changes only)' if not args.all else 'OFF (all packets)'}")
    print(f"Mode       : {'JSON output' if args.json else 'Text output'}")
    if args.timeout > 0:
        print(f"Timeout    : {args.timeout} seconds")
    else:
        print("Timeout    : Indefinite (Press Ctrl+C to stop)")
    print("------------------------------------------------")

    scanner = SwitchBotPlugScanner(
        callback=lambda data: handle_packet(data, args.json, args.debug),
        target_mac=args.mac,
        deduplicate=not args.all,
        debug=args.debug,
    )

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            # Windows or restricted environments might not support signal handlers on loop
            pass

    async def scan_task():
        try:
            await scanner.scan(timeout=args.timeout if args.timeout > 0 else None)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(scan_task())

    try:
        if args.timeout > 0:
            await task
        else:
            await stop_event.wait()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    except KeyboardInterrupt:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    finally:
        print("\nScan completed.")


def main(argv: Optional[list] = None) -> int:
    """Entrypoint for CLI."""
    parser = argparse.ArgumentParser(
        prog="switchbot-plug",
        description="SwitchBot Plug Mini BLE Advertisement Scanner (Cross-platform Python)",
    )
    parser.add_argument(
        "-m",
        "--mac",
        type=str,
        default=None,
        help="Target MAC address to filter (e.g. 0C:4E:A0:36:08:46).",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Disable deduplication; show every received advertisement packet.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logs and hex dump of raw advertisement payload.",
    )
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        help="Output data as newline-delimited JSON objects.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=0.0,
        help="Scan timeout in seconds (0 = continuous until Ctrl+C).",
    )

    args = parser.parse_args(argv)

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
