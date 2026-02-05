"""
UPnP discovery: find all devices, then filter to MediaRenderers (can play music).
"""
from typing import Any

import aiohttp
from async_upnp_client.aiohttp import AiohttpSessionRequester
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.search import async_search
from async_upnp_client.utils import CaseInsensitiveDict


# SSDP search target: all devices (we filter to MediaRenderer by checking AVTransport)
SSDP_ST_ALL = "ssdp:all"
SSDP_MX = 5  # seconds to wait for responses


async def discover_media_renderers(timeout: int = SSDP_MX) -> list[dict[str, Any]]:
    """
    Run SSDP discovery and return list of MediaRenderer devices.
    Each item: {"name": str, "description_url": str}.
    """
    seen_locations: set[str] = set()
    collected: list[CaseInsensitiveDict] = []

    async def collect(headers: CaseInsensitiveDict) -> None:
        location = (headers.get("location") or headers.get("Location") or "").strip()
        if location and location not in seen_locations:
            seen_locations.add(location)
            collected.append(headers)

    await async_search(async_callback=collect, timeout=timeout, search_target=SSDP_ST_ALL)

    renderers: list[dict[str, Any]] = []
    async with aiohttp.ClientSession() as session:
        requester = AiohttpSessionRequester(session)
        factory = UpnpFactory(requester, non_strict=True)
        for headers in collected:
            location = (headers.get("location") or headers.get("Location") or "").strip()
            if not location:
                continue
            try:
                device = await factory.async_create_device(location)
            except Exception:
                continue
            # Check if it has AVTransport (can play media)
            # device.services is a dict {service_type: UpnpService}; use .values() to get services
            avt = None
            for svc in device.all_services:
                if "AVTransport" in (svc.service_type or ""):
                    avt = svc
                    break
            if avt is None:
                continue
            name = (device.name or "Unknown").strip() or location
            renderers.append({
                "name": name,
                "description_url": location,
            })

    return renderers
