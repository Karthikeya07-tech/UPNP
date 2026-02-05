"""
Play a media URL on a UPnP MediaRenderer (AVTransport).
Stop playback and read position (for progress bar) via AVTransport actions.
"""
from __future__ import annotations

import re
from typing import Any

import aiohttp
from async_upnp_client.aiohttp import AiohttpSessionRequester
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.client import UpnpDevice, UpnpService


def _find_avtransport(device: UpnpDevice) -> UpnpService | None:
    # device.services is a dict {service_type: UpnpService}; all_services yields actual services
    for svc in device.all_services:
        if "AVTransport" in (svc.service_type or ""):
            return svc
    return None


def _time_str_to_seconds(s: str) -> float:
    """Convert UPnP time string (H:MM:SS or HH:MM:SS) to seconds. Returns 0.0 on parse error."""
    if not s or s == "NOT_IMPLEMENTED":
        return 0.0
    m = re.match(r"^(\d+):(\d{2}):(\d{2})$", s.strip())
    if m:
        h, m_, sec = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return h * 3600 + m_ * 60 + sec
    return 0.0


def _seconds_to_str(sec: float) -> str:
    """Convert seconds to M:SS for display."""
    if sec <= 0 or sec != sec:
        return "0:00"
    m = int(sec // 60)
    s = int(sec % 60)
    if m >= 60:
        h, m = m // 60, m % 60
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


async def play_media(description_url: str, media_url: str) -> None:
    """
    Set media URL on the renderer and start playback.
    media_url must be an absolute HTTP/HTTPS URL reachable by the renderer.
    """
    async with aiohttp.ClientSession() as session:
        requester = AiohttpSessionRequester(session)
        factory = UpnpFactory(requester, non_strict=True)
        device = await factory.async_create_device(description_url)
        avt = _find_avtransport(device)
        if avt is None:
            raise RuntimeError("Device has no AVTransport service (not a MediaRenderer)")
        await avt.async_call_action("SetAVTransportURI", InstanceID=0, CurrentURI=media_url, CurrentURIMetaData="")
        await avt.async_call_action("Play", InstanceID=0, Speed="1")


async def stop_media(description_url: str) -> None:
    """Stop playback on the renderer (AVTransport Stop)."""
    async with aiohttp.ClientSession() as session:
        requester = AiohttpSessionRequester(session)
        factory = UpnpFactory(requester, non_strict=True)
        device = await factory.async_create_device(description_url)
        avt = _find_avtransport(device)
        if avt is None:
            raise RuntimeError("Device has no AVTransport service (not a MediaRenderer)")
        await avt.async_call_action("Stop", InstanceID=0)


async def get_position_info(description_url: str) -> dict[str, Any]:
    """
    Get current playback position from the renderer (GetPositionInfo).
    Returns dict with RelTime, TrackDuration (UPnP strings), elapsed_sec, duration_sec, and state.
    """
    async with aiohttp.ClientSession() as session:
        requester = AiohttpSessionRequester(session)
        factory = UpnpFactory(requester, non_strict=True)
        device = await factory.async_create_device(description_url)
        avt = _find_avtransport(device)
        if avt is None:
            raise RuntimeError("Device has no AVTransport service (not a MediaRenderer)")
        out = await avt.async_call_action("GetPositionInfo", InstanceID=0)
        rel = (out.get("RelTime") or "").strip()
        dur = (out.get("TrackDuration") or "").strip()
        return {
            "RelTime": rel,
            "TrackDuration": dur,
            "elapsed_sec": _time_str_to_seconds(rel),
            "duration_sec": _time_str_to_seconds(dur),
            "TransportState": out.get("TransportState", ""),
        }


def format_progress(elapsed_sec: float, duration_sec: float, width: int = 24) -> str:
    """Build a single-line progress bar: [=====>    ] 1:23 / 3:45 (33%)."""
    if duration_sec <= 0:
        return f"[{'?':<{width}}] {_seconds_to_str(elapsed_sec)} / --"
    pct = min(1.0, elapsed_sec / duration_sec)
    filled = int(width * pct)
    bar = "=" * filled + ">" * (1 if filled < width else 0) + " " * (width - filled - 1)
    return f"[{bar}] {_seconds_to_str(elapsed_sec)} / {_seconds_to_str(duration_sec)} ({int(pct * 100)}%)"
