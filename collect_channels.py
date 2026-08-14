#!/usr/bin/env python3
"""
IPTV Channel Link Collector - India & Bangladesh
"""

import json
import urllib.request
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys

API_BASE = "https://iptv-org.github.io/api/"
TARGET_COUNTRIES = {"IN", "BD"}
OUTPUT_JSON = "channels_ind_bd.json"
OUTPUT_M3U = "playlist_ind_bd.m3u8"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def load_previous_data(filepath: str):
    path = Path(filepath)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Could not read previous data: {e}")
    return []

def save_json(data, filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"Saved JSON: {filepath}")

def generate_m3u(channels, filepath: str):
    lines = ["#EXTM3U"]
    for ch in channels:
        name = ch.get("name", "Unknown")
        logo = ch.get("logo", "")
        group = ch.get("country", "")
        url = ch.get("url", "")
        if not url:
            continue
        lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name}')
        lines.append(url)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log.info(f"Saved M3U: {filepath}")

def main():
    log.info("Starting IPTV link collection...")

    try:
        channels_data = fetch_json(API_BASE + "channels.json")
        streams_data = fetch_json(API_BASE + "streams.json")
        logos_data = fetch_json(API_BASE + "logos.json")   # logos.json ফেচ
    except Exception as e:
        log.error(f"Failed to fetch API data: {e}")
        sys.exit(1)

    channel_map = {ch["id"]: ch for ch in channels_data}

    # লোগো ম্যাপ তৈরি
    logo_map = {}
    for logo_entry in logos_data:
        ch_id = logo_entry.get("channel")
        url = logo_entry.get("url")
        if ch_id and url and ch_id not in logo_map:
            logo_map[ch_id] = url

    filtered_channels = []
    for stream in streams_data:
        cid = stream.get("channel")
        if not cid:
            continue
        country = channel_map.get(cid, {}).get("country")
        if country in TARGET_COUNTRIES:
            ch_info = channel_map[cid]
            # লোগো: আগে channels.json থেকে, না থাকলে logos.json
            logo = ch_info.get("logo") or logo_map.get(cid, "")
            filtered_channels.append({
                "id": cid,
                "name": ch_info.get("name", cid),
                "country": country,
                "url": stream.get("url", ""),
                "logo": logo,
                "categories": ch_info.get("categories", []),
                "last_updated": datetime.now(timezone.utc).isoformat()
            })

    log.info(f"Found {len(filtered_channels)} channels for IN/BD")

    previous = load_previous_data(OUTPUT_JSON)
    prev_map = {ch["id"]: ch for ch in previous}

    new_channels = [ch for ch in filtered_channels if ch["id"] not in prev_map]
    removed_channels = [ch for ch in previous if ch["id"] not in {c["id"] for c in filtered_channels}]
    changed_channels = []
    for new_ch in filtered_channels:
        old_ch = prev_map.get(new_ch["id"])
        if old_ch and old_ch.get("url") != new_ch.get("url"):
            changed_channels.append({
                "id": new_ch["id"],
                "name": new_ch["name"],
                "old_url": old_ch.get("url"),
                "new_url": new_ch.get("url")
            })

    if new_channels:
        log.info(f"➕ New channels: {len(new_channels)}")
    if removed_channels:
        log.info(f"❌ Removed channels: {len(removed_channels)}")
    if changed_channels:
        log.info(f"🔄 Changed URLs: {len(changed_channels)}")

    save_json(filtered_channels, OUTPUT_JSON)
    generate_m3u(filtered_channels, OUTPUT_M3U)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_channels": len(filtered_channels),
        "new": len(new_channels),
        "removed": len(removed_channels),
        "changed": len(changed_channels)
    }
    with open("last_run_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"Summary: {summary}")

    log.info("Done.")

if __name__ == "__main__":
    main()
