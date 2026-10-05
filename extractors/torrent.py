import os
import re
import sys
import time
import base64
import hashlib
import logging
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

logger = logging.getLogger(__name__)

# File extension categorizers
VIDEO_EXTS = {'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'ts', 'mpg', 'mpeg', 'm4v', '3gp', 'm2ts', 'vob', 'ogv'}
AUDIO_EXTS = {'mp3', 'm4a', 'wav', 'flac', 'ogg', 'aac', 'wma', 'opus', 'alac', 'aiff', 'mka'}
IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'heif', 'tiff', 'tif', 'svg', 'ico', 'avif'}
SUB_EXTS = {'vtt', 'srt', 'ass', 'ssa', 'sub', 'idx', 'lrc'}
TEXT_EXTS = {'xml', 'json', 'txt', 'csv', 'log', 'md', 'html', 'htm', 'css', 'js', 'py', 'yaml', 'yml', 'ini', 'cfg', 'conf', 'sql', 'nfo'}
DOC_EXTS = {'pdf', 'doc', 'docx', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx'}
DATA_EXTS = {'sqlite', 'db', 'sqlite3', 'dat', 'bin', 'cue', 'iso', 'img', 'bak', 'dump'}
ARCHIVE_EXTS = {'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'dmg', 'exe', 'msi', 'apk'}

def format_size(size_bytes):
    """Format bytes into readable units."""
    if not size_bytes or size_bytes <= 0:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}" if unit in ['MB', 'GB', 'TB'] else f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def bdecode_torrent(data):
    """
    Pure Python Bencode decoder (BEP 0003).
    Returns (decoded_dict, sha1_info_hash).
    """
    info_raw = None

    def decode_item(idx, parent_key=None):
        nonlocal info_raw
        if idx >= len(data):
            raise ValueError("Unexpected end of bencoded data")
        char = data[idx:idx+1]

        if char == b'i':
            end = data.index(b'e', idx)
            return int(data[idx+1:end]), end + 1

        elif char == b'l':
            idx += 1
            items = []
            while data[idx:idx+1] != b'e':
                item, idx = decode_item(idx)
                items.append(item)
            return items, idx + 1

        elif char == b'd':
            idx += 1
            d = {}
            while data[idx:idx+1] != b'e':
                key, idx = decode_item(idx)
                val_start = idx
                val, idx = decode_item(idx, key)
                if key == b'info':
                    info_raw = data[val_start:idx]
                d[key] = val
            return d, idx + 1

        elif char.isdigit():
            colon = data.index(b':', idx)
            length = int(data[idx:colon])
            start = colon + 1
            end = start + length
            return data[start:end], end

        raise ValueError(f"Invalid bencode character at byte offset {idx}: {char!r}")

    parsed = decode_item(0)[0]
    info_hash = hashlib.sha1(info_raw).hexdigest() if info_raw else ""
    return parsed, info_hash

def _decode_str(b_val, fallback=""):
    """Safely decode bytes to string."""
    if b_val is None:
        return fallback
    if isinstance(b_val, str):
        return b_val
    if isinstance(b_val, bytes):
        for enc in ['utf-8', 'cp1252', 'latin-1']:
            try:
                return b_val.decode(enc)
            except Exception:
                pass
        return b_val.decode('utf-8', errors='replace')
    return str(b_val)

def is_torrent_input(url_or_path):
    """Check if input is a Magnet URI, .torrent file/URL, or 40-char torrent hash."""
    if not url_or_path:
        return False
    target = re.sub(r'^[\'"]+|[\'"]+$', '', str(url_or_path).strip()).strip()
    if target.lower().startswith("magnet:?"):
        return True
    if target.lower().endswith(".torrent") or ".torrent?" in target.lower():
        return True
    # 40-character hex info-hash (e.g. 3b10b054b1680110d403788034f51763ac43791e)
    if re.match(r'^[a-fA-F0-9]{40}$', target):
        return True
    # 32-character base32 info-hash
    if len(target) == 32 and re.match(r'^[2-7A-Za-z]+$', target):
        return True
    # Local existing .torrent file
    if os.path.isfile(target) and target.lower().endswith(".torrent"):
        return True
    return False

def parse_magnet_uri(magnet_uri):
    """Extract parameters from a Magnet URI."""
    clean = magnet_uri.strip()
    parsed = urlparse(clean)
    qs = parse_qs(parsed.query)

    xt_list = qs.get("xt", [])
    info_hash = ""
    for xt in xt_list:
        match = re.search(r'urn:btih:([a-zA-Z0-9]+)', xt, re.IGNORECASE)
        if match:
            h = match.group(1)
            if len(h) == 32:
                try:
                    info_hash = base64.b32decode(h.upper()).hex().lower()
                except Exception:
                    info_hash = h.lower()
            else:
                info_hash = h.lower()
            break

    dn_list = qs.get("dn", [])
    display_name = unquote(dn_list[0]) if dn_list else ""
    if not display_name and info_hash:
        display_name = f"Torrent [{info_hash[:10]}...]"

    trackers = [unquote(t) for t in qs.get("tr", [])]
    xl = qs.get("xl", [None])[0]
    total_bytes = int(xl) if (xl and str(xl).isdigit()) else None

    return {
        "info_hash": info_hash,
        "name": display_name or "BitTorrent Swarm",
        "trackers": trackers,
        "total_bytes": total_bytes,
        "raw_magnet": clean
    }

def extract_torrent_info(url_or_path, client_id=None):
    """
    Analyze and extract metadata from Magnet link, .torrent file path, or .torrent URL.
    Returns dictionary conforming to /api/info specification.
    """
    target = re.sub(r'^[\'"]+|[\'"]+$', '', str(url_or_path).strip()).strip()

    # 1. Convert bare hash to magnet URI
    if re.match(r'^[a-fA-F0-9]{40}$', target):
        target = f"magnet:?xt=urn:btih:{target.lower()}"
    elif len(target) == 32 and re.match(r'^[2-7A-Za-z]+$', target):
        try:
            hex_hash = base64.b32decode(target.upper()).hex().lower()
            target = f"magnet:?xt=urn:btih:{hex_hash}"
        except Exception:
            target = f"magnet:?xt=urn:btih:{target}"

    # Default branding icon (uTorrent/BitTorrent green branding)
    torrent_thumb = "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?q=80&w=480"

    # Case A: Magnet Link
    if target.lower().startswith("magnet:?"):
        magnet_data = parse_magnet_uri(target)
        info_hash = magnet_data["info_hash"]
        title = magnet_data["name"]
        trackers = magnet_data["trackers"]
        total_bytes = magnet_data["total_bytes"]
        formatted_size = format_size(total_bytes) if total_bytes else "P2P Swarm (Metadata on connect)"

        tracker_summary = f"{len(trackers)} Tracker(s)" if trackers else "DHT / Peer Exchange"
        main_tracker = urlparse(trackers[0]).netloc if trackers else "P2P BitTorrent Network"

        # Provide options: Open in torrent client or copy magnet
        video_options = [
            {
                "format_id": "torrent_magnet_open",
                "label": "Open in uTorrent / BitTorrent Client",
                "resolution": "Magnet Handoff",
                "ext": "magnet",
                "url": target,
                "size": formatted_size,
                "type": "torrent",
                "quality": "Direct P2P",
                "is_torrent": True,
                "is_package": True
            },
            {
                "format_id": "torrent_magnet_save",
                "label": "Save .magnet Link Shortcut File",
                "resolution": f"Hash: {info_hash[:12]}...",
                "ext": "magnet",
                "url": target,
                "size": "1 KB",
                "type": "torrent",
                "quality": "Text Link",
                "is_torrent": True,
                "is_package": True
            }
        ]

        description = (
            f"BitTorrent Magnet Link\n"
            f"Info Hash: {info_hash}\n"
            f"Trackers ({len(trackers)}):\n" + "\n".join(trackers[:8])
        )

        return {
            "status": "success",
            "id": info_hash,
            "webpage_url": target,
            "title": title,
            "uploader": f"uTorrent / {main_tracker}",
            "duration": formatted_size,
            "duration_raw": total_bytes or 0,
            "thumbnail": torrent_thumb,
            "platform_label": "uTorrent / Magnet",
            "platform_class": "torrent",
            "views": "Magnet URI",
            "likes": tracker_summary,
            "upload_date": datetime.now().strftime("%d/%m/%Y"),
            "description": description,
            "category": "BitTorrent",
            "tags": ["torrent", "magnet", "p2p", "utorrent"],
            "video_options": video_options,
            "audio_options": [],
            "subtitles": [],
            "images": [],
            "is_torrent": True
        }

    # Case B: .torrent file (Local path or Remote URL)
    raw_data = None
    if os.path.isfile(target):
        try:
            with open(target, "rb") as f:
                raw_data = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read local torrent file: {str(e)}")
    elif target.lower().startswith("http://") or target.lower().startswith("https://"):
        try:
            import requests
            resp = requests.get(target, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            raw_data = resp.content
        except Exception as e:
            raise ValueError(f"Failed to fetch .torrent from URL: {str(e)}")
    else:
        raise ValueError("Invalid torrent file path or URL.")

    # Decode bencoded torrent
    parsed_torrent, info_hash = bdecode_torrent(raw_data)
    info_dict = parsed_torrent.get(b'info', {})

    # Torrent Name
    name = _decode_str(info_dict.get(b'name.utf-8') or info_dict.get(b'name'), "Untitled Torrent")
    comment = _decode_str(parsed_torrent.get(b'comment.utf-8') or parsed_torrent.get(b'comment'), "")
    created_by = _decode_str(parsed_torrent.get(b'created by'), "BitTorrent Client")
    
    creation_date = parsed_torrent.get(b'creation date')
    if creation_date and isinstance(creation_date, int):
        formatted_date = datetime.fromtimestamp(creation_date).strftime("%d/%m/%Y %H:%M")
    else:
        formatted_date = datetime.now().strftime("%d/%m/%Y")

    # Trackers
    trackers = []
    announce = _decode_str(parsed_torrent.get(b'announce'))
    if announce:
        trackers.append(announce)
    announce_list = parsed_torrent.get(b'announce-list', [])
    for tier in announce_list:
        if isinstance(tier, list):
            for tr in tier:
                t_str = _decode_str(tr)
                if t_str and t_str not in trackers:
                    trackers.append(t_str)

    # Parse files inside the torrent
    files_list = []
    total_size = 0

    if b'files' in info_dict and isinstance(info_dict[b'files'], list):
        # Multi-file torrent
        for idx, f in enumerate(info_dict[b'files']):
            f_len = f.get(b'length', 0)
            total_size += f_len
            path_parts = f.get(b'path.utf-8') or f.get(b'path', [])
            decoded_parts = [_decode_str(p) for p in path_parts]
            rel_path = "/".join(decoded_parts) if decoded_parts else f"file_{idx}"
            ext = rel_path.split(".")[-1].lower() if "." in rel_path else ""
            files_list.append({
                "index": idx,
                "path": rel_path,
                "size": f_len,
                "ext": ext
            })
    else:
        # Single-file torrent
        single_len = info_dict.get(b'length', 0)
        total_size = single_len
        ext = name.split(".")[-1].lower() if "." in name else ""
        files_list.append({
            "index": 0,
            "path": name,
            "size": single_len,
            "ext": ext
        })

    # BEP 19 WebSeeds (HTTP streaming fallback for archive.org & web-seeded swarms)
    webseeds = []
    raw_url_list = parsed_torrent.get(b'url-list')
    if raw_url_list:
        if isinstance(raw_url_list, list):
            for u in raw_url_list:
                s = _decode_str(u).strip()
                if s:
                    webseeds.append(s)
        else:
            s = _decode_str(raw_url_list).strip()
            if s:
                webseeds.append(s)

    # Sort files: largest or videos first
    video_options = []
    audio_options = []
    images = []

    # Dedicated Option for full torrent package
    video_options.append({
        "format_id": "torrent_file_download",
        "label": f"Download Torrent File ({len(files_list)} files enclosed)",
        "resolution": "Full Swarm Package",
        "ext": "torrent",
        "url": target if target.startswith("http") else "",
        "size": format_size(total_size),
        "type": "torrent",
        "quality": "Original .torrent",
        "is_torrent": True,
        "is_package": True
    })

    torrent_dir = os.path.dirname(os.path.abspath(target)) if (os.path.isfile(target)) else ""

    for f in files_list:
        ext = f["ext"]
        f_size_str = format_size(f["size"])
        opt = {
            "format_id": f"torrent_content_{f['index']}",
            "label": f["path"],
            "resolution": ext.upper() if ext else "FILE",
            "ext": ext or "dat",
            "size": f_size_str,
            "quality": "Torrent Enclosed File",
            "is_torrent": True
        }
        # 1. ponytail: If file already downloaded next to .torrent, link path directly for direct local preview
        if torrent_dir:
            cand_paths = [
                os.path.join(torrent_dir, f["path"]),
                os.path.join(torrent_dir, name, f["path"]),
                os.path.join(torrent_dir, os.path.basename(f["path"]))
            ]
            for cand in cand_paths:
                if os.path.isfile(cand):
                    opt["url"] = cand.replace('\\', '/')
                    opt["is_local"] = True
                    break

        # 2. ponytail: BEP 19 WebSeeds - If not on disk, resolve direct HTTP URL for on-the-fly streaming/preview
        if not opt.get("url") and webseeds:
            import urllib.parse
            base_seed = webseeds[0]
            if not base_seed.endswith('/'):
                base_seed += '/'
            if len(files_list) == 1 and not (b'files' in info_dict):
                opt["url"] = urllib.parse.urljoin(base_seed, urllib.parse.quote(name))
            else:
                prefix = "" if base_seed.rstrip('/').endswith(name) else f"{name}/"
                opt["url"] = urllib.parse.urljoin(base_seed, f"{prefix}{urllib.parse.quote(f['path'])}")
            opt["is_webseed"] = True

        # Proper file categorization by extension
        if ext in VIDEO_EXTS:
            opt["type"] = "video"
            video_options.append(opt)
        elif ext in AUDIO_EXTS:
            opt["type"] = "audio"
            audio_options.append(opt)
        elif ext in IMAGE_EXTS:
            opt["type"] = "image"
            video_options.append(opt)
            images.append({
                "url": opt.get("url") or torrent_thumb,
                "label": f["path"],
                "size": f_size_str,
                "ext": ext
            })
        elif ext in SUB_EXTS:
            opt["type"] = "subtitle"
            video_options.append(opt)
        elif ext in TEXT_EXTS:
            opt["type"] = "text"
            video_options.append(opt)
        elif ext in DOC_EXTS:
            opt["type"] = "document"
            video_options.append(opt)
        elif ext in DATA_EXTS:
            opt["type"] = "data"
            video_options.append(opt)
        elif ext in ARCHIVE_EXTS:
            opt["type"] = "archive"
            video_options.append(opt)
        else:
            opt["type"] = "other"
            video_options.append(opt)

    canonical_magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={unquote(name)}"
    if trackers:
        canonical_magnet += f"&tr={unquote(trackers[0])}"

    desc = (
        f"BitTorrent .torrent Package\n"
        f"Info Hash: {info_hash}\n"
        f"Client: {created_by}\n"
        f"Files enclosed: {len(files_list)}\n"
        f"{comment}"
    )

    return {
        "status": "success",
        "id": info_hash,
        "webpage_url": canonical_magnet,
        "title": name,
        "uploader": f"{created_by} / uTorrent",
        "duration": format_size(total_size),
        "duration_raw": total_size,
        "thumbnail": torrent_thumb,
        "platform_label": "uTorrent / BitTorrent",
        "platform_class": "torrent",
        "views": f"{len(files_list)} File(s)",
        "likes": f"{len(trackers)} Tracker(s)",
        "upload_date": formatted_date,
        "description": desc,
        "category": "BitTorrent",
        "tags": ["torrent", "utorrent", "bittorrent", "p2p"],
        "video_options": video_options,
        "audio_options": audio_options,
        "subtitles": [],
        "images": images,
        "is_torrent": True
    }
