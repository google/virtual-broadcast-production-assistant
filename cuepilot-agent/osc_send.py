#!/usr/bin/env python3
"""
Simple OSC sender.

Usage examples:
  python osc_send.py --host 127.0.0.1 --port 9090 /cuepilot/transport/play
  python osc_send.py -H 192.168.1.50 -P 53311 /cuepilot/transport/setspeed 1.25
  python osc_send.py -H 192.168.1.50 -P 53311 /cuepilot/transport/jumpto "00:01:23" 0 0.0
"""
import argparse
from pythonosc.udp_client import SimpleUDPClient

def parse_arg(s: str):
    # Try to coerce types: int -> float -> str
    # (CuePilot may expect specific types: i, f, s)
    try:
        if s.lower().startswith(("0x", "0o", "0b")):
            return int(s, 0)
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def main():
    p = argparse.ArgumentParser(description="Send a single OSC message.")
    p.add_argument("address", help="OSC address, e.g. /cuepilot/transport/play")
    p.add_argument("args", nargs="*", help="Optional OSC arguments")
    p.add_argument("-H", "--host", default="127.0.0.1", help="OSC target host (default: 127.0.0.1)")
    p.add_argument("-P", "--port", default=53311, type=int, help="OSC target port (default: 9090)")
    args = p.parse_args()

    client = SimpleUDPClient(args.host, args.port)
    payload = [parse_arg(a) for a in args.args]
    client.send_message(args.address, payload)
    print(f"Sent -> {args.host}:{args.port}  {args.address} {payload}")

if __name__ == "__main__":
    main()