#!/usr/bin/env python3
"""
UPnP music player for Termux: discover MediaRenderer devices, pick one, play a URL or local file.
Run: python main.py
"""
import asyncio
import os
import sys

from upnp_discovery import discover_media_renderers
from upnp_player import play_media, stop_media, get_position_info, format_progress
from serve_file import serve_file_once


def prompt(text: str, default: str = "") -> str:
    """Read a line from stdin (Termux-friendly)."""
    if default:
        sys.stdout.write(f"{text} [{default}]: ")
    else:
        sys.stdout.write(f"{text}: ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return default
    return line.strip() or default


def prompt_int(text: str, min_val: int, max_val: int) -> int:
    """Read an integer in range from stdin."""
    while True:
        raw = prompt(text)
        try:
            n = int(raw)
            if min_val <= n <= max_val:
                return n
        except ValueError:
            pass
        print(f"Enter a number between {min_val} and {max_val}")


async def main() -> None:
    print("UPnP Music Player (Termux)")
    print("Make sure your phone is on the same WiFi as the speaker/TV.\n")

    print("Discovering UPnP devices (MediaRenderers)...")
    try:
        renderers = await discover_media_renderers(timeout=6)
    except Exception as e:
        print(f"Discovery failed: {e}")
        sys.exit(1)

    if not renderers:
        print("No MediaRenderer devices found. Check WiFi and try again.")
        sys.exit(1)

    print(f"\nFound {len(renderers)} device(s):")
    for i, r in enumerate(renderers, 1):
        print(f"  {i}. {r['name']}")
    idx = prompt_int("Select device", 1, len(renderers))
    chosen = renderers[idx - 1]
    description_url = chosen["description_url"]
    print(f"Using: {chosen['name']}\n")

    media_input = prompt(
        "Enter music: URL (http/https) or path to a local file",
        default="",
    ).strip()
    if not media_input:
        print("Nothing to play.")
        sys.exit(0)

    media_url: str
    stop_server = None

    if media_input.startswith("http://") or media_input.startswith("https://"):
        media_url = media_input
    else:
        # Local file: serve it over HTTP so the renderer can fetch it
        if not os.path.isfile(media_input):
            abs_path = os.path.abspath(media_input)
            print(f"File not found: {abs_path}")
            sys.exit(1)
        print("Serving file on this device; renderer will stream from it.")
        try:
            media_url, stop_server = serve_file_once(media_input)
            print(f"Local URL: {media_url}")
        except Exception as e:
            print(f"Could not serve file: {e}")
            sys.exit(1)

    print("Sending to device and starting playback...")
    try:
        await play_media(description_url, media_url)
    except Exception as e:
        print(f"Play failed: {e}")
        if stop_server:
            stop_server()
        sys.exit(1)

    print("Playing. Press Enter to stop.\n")
    stop_requested = False
    poll_interval = 1.5

    async def poll_position() -> None:
        nonlocal stop_requested
        while not stop_requested:
            try:
                info = await get_position_info(description_url)
                state = (info.get("TransportState") or "").upper()
                if state in ("STOPPED", ""):
                    break
                elapsed = info.get("elapsed_sec") or 0.0
                duration = info.get("duration_sec") or 0.0
                line = (format_progress(elapsed, duration) + "  (Enter = stop)").ljust(72)
                sys.stdout.write("\r" + line)
                sys.stdout.flush()
            except Exception:
                pass
            await asyncio.sleep(poll_interval)

    async def wait_stop() -> None:
        nonlocal stop_requested
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sys.stdin.readline)
        stop_requested = True

    try:
        poll_task = asyncio.create_task(poll_position())
        stop_task = asyncio.create_task(wait_stop())
        done, _ = await asyncio.wait(
            [poll_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_task in done:
            poll_task.cancel()
            try:
                await poll_task
            except asyncio.CancelledError:
                pass
            await stop_media(description_url)
            print("\nStopped.")
        else:
            stop_task.cancel()
            try:
                await stop_task
            except asyncio.CancelledError:
                pass
            print("\nPlayback ended on device.")
    finally:
        if stop_server:
            stop_server()
            print("Stopped file server.")


if __name__ == "__main__":
    asyncio.run(main())
