#!/usr/bin/env python3
"""Add the kitten overlay to the current OBS scene collection.

Quit OBS before running this. OBS rewrites the scene file on exit, so a
change made while it is open is discarded.
"""

import argparse
import configparser
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OVERLAY = ROOT / "overlay.html"
SCRIPT = ROOT / "meow-for-e-kittens.lua"
SOURCE_NAME = "Kittens"
HOTKEY_SETTING = "meow_for_e_kittens.trigger"

CONFIG_CANDIDATES = (
    Path.home() / ".var/app/com.obsproject.Studio/config/obs-studio",
    Path.home() / ".config/obs-studio",
)


def obs_is_running():
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "comm").read_text(errors="replace").strip()
        except OSError:
            continue
        # Browser helper processes are named obs-browser-page. Only the app itself is "obs".
        if command == "obs":
            return True
    return False


def read_ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path)
    return parser


def config_dirs():
    found = [path for path in CONFIG_CANDIDATES if (path / "user.ini").is_file()]
    if not found:
        return []
    return sorted(found, key=lambda path: (path / "user.ini").stat().st_mtime, reverse=True)


def canvas_size(config_dir):
    user = read_ini(config_dir / "user.ini")
    profile = user.get("Basic", "ProfileDir", fallback="Untitled")
    basic_path = config_dir / "basic" / "profiles" / profile / "basic.ini"
    if not basic_path.is_file():
        return 1920, 1080
    basic = read_ini(basic_path)
    return (
        basic.getint("Video", "BaseCX", fallback=1920),
        basic.getint("Video", "BaseCY", fallback=1080),
    )


def scene_path(config_dir):
    user = read_ini(config_dir / "user.ini")
    name = user.get("Basic", "SceneCollection", fallback="Untitled")
    filename = user.get("Basic", "SceneCollectionFile", fallback="Untitled.json")
    return name, config_dir / "basic" / "scenes" / filename


def obs_key(text):
    token = text.strip().upper()
    if len(token) == 1 and "A" <= token <= "Z":
        return f"OBS_KEY_{token}"
    if token.startswith("F") and token[1:].isdigit() and 1 <= int(token[1:]) <= 12:
        return f"OBS_KEY_{token}"
    raise SystemExit("Use a letter or F1 through F12, for example: python3 install.py --key F8")


def same_file(left, right):
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return False


def fullscreen_geometry(width, height):
    return {
        "scale_ref": {"x": float(width), "y": float(height)},
        "pos": {"x": 0.0, "y": 0.0},
        "pos_rel": {"x": -float(width) / float(height), "y": -1.0},
        "scale": {"x": 1.0, "y": 1.0},
        "scale_rel": {"x": 1.0, "y": 1.0},
        "bounds": {"x": 0.0, "y": 0.0},
        "bounds_rel": {"x": 0.0, "y": 0.0},
    }


def browser_source(name, source_uuid, width, height, prev_ver):
    return {
        "prev_ver": prev_ver,
        "name": name,
        "uuid": source_uuid,
        "id": "browser_source",
        "versioned_id": "browser_source",
        "settings": {
            "is_local_file": True,
            "local_file": str(OVERLAY),
            "width": width,
            "height": height,
            "fps_custom": True,
            "fps": 60,
            "shutdown": False,
            "restart_when_active": False,
        },
        "mixers": 255,
        "sync": 0,
        "flags": 0,
        "volume": 1.0,
        "balance": 0.5,
        "enabled": True,
        "muted": False,
        "push-to-mute": False,
        "push-to-mute-delay": 0,
        "push-to-talk": False,
        "push-to-talk-delay": 0,
        "hotkeys": {
            "libobs.mute": [],
            "libobs.unmute": [],
            "libobs.monitor-on": [],
            "libobs.monitor-off": [],
            "libobs.push-to-mute": [],
            "libobs.push-to-talk": [],
            "ObsBrowser.Refresh": [],
        },
        "deinterlace_mode": 0,
        "deinterlace_field_order": 0,
        "monitoring_type": 0,
        "monitoring_enabled": False,
        "private_settings": {},
    }


def scene_item(name, source_uuid, item_id, width, height):
    item = {
        "name": name,
        "source_uuid": source_uuid,
        "visible": True,
        "locked": False,
        "rot": 0.0,
        "align": 5,
        "bounds_type": 0,
        "bounds_align": 0,
        "bounds_crop": False,
        "crop_left": 0,
        "crop_top": 0,
        "crop_right": 0,
        "crop_bottom": 0,
        "id": item_id,
        "group_item_backup": False,
        "scale_filter": "disable",
        "blend_method": "default",
        "blend_type": "normal",
        "show_transition": {"duration": 300},
        "hide_transition": {"duration": 300},
        "private_settings": {},
    }
    item.update(fullscreen_geometry(width, height))
    return item


def find_source(collection):
    matches = []
    for source in collection.get("sources", []):
        settings = source.get("settings") or {}
        if source.get("id") != "browser_source":
            continue
        if same_file(settings.get("local_file", ""), OVERLAY) or source.get("name") == SOURCE_NAME:
            matches.append(source)
    for source in matches:
        if same_file((source.get("settings") or {}).get("local_file", ""), OVERLAY):
            return source
    return matches[0] if matches else None


def configure_source(source, width, height):
    settings = source.setdefault("settings", {})
    settings["is_local_file"] = True
    settings["local_file"] = str(OVERLAY)
    settings["width"] = width
    settings["height"] = height
    settings["fps_custom"] = True
    settings["fps"] = 60
    settings["shutdown"] = False
    settings["restart_when_active"] = False
    source["enabled"] = True


def place_on_scene(scene, source, width, height):
    settings = scene.setdefault("settings", {})
    items = settings.setdefault("items", [])
    name = source["name"]
    source_uuid = source["uuid"]
    existing = [
        item
        for item in items
        if item.get("source_uuid") == source_uuid or item.get("name") == name
    ]
    if existing:
        item = existing[0]
        item["name"] = name
        item["source_uuid"] = source_uuid
        item["visible"] = True
        item.update(fullscreen_geometry(width, height))
        items[:] = [entry for entry in items if entry is not item]
        items.append(item)
        return

    counter = int(settings.get("id_counter") or 0) + 1
    settings["id_counter"] = counter
    items.append(scene_item(name, source_uuid, counter, width, height))


def hotkey_label(binding):
    if not binding:
        return "not set"
    key = binding[0].get("key", "OBS_KEY_NONE").removeprefix("OBS_KEY_")
    parts = []
    for name in ("control", "alt", "shift", "command"):
        if binding[0].get(name):
            parts.append(name)
    parts.append(key)
    return "+".join(parts)


def install_script(collection, source_name, key_name):
    modules = collection.setdefault("modules", {})
    scripts = modules.setdefault("scripts-tool", [])
    if not isinstance(scripts, list):
        scripts = []
        modules["scripts-tool"] = scripts

    entry = None
    for candidate in scripts:
        if same_file(candidate.get("path", ""), SCRIPT):
            entry = candidate
            break

    if entry is None:
        entry = {"path": str(SCRIPT), "settings": {}}
        scripts.append(entry)

    entry["path"] = str(SCRIPT)
    settings = entry.setdefault("settings", {})
    settings["source"] = source_name
    current = settings.get(HOTKEY_SETTING) or []
    if key_name or not current:
        settings[HOTKEY_SETTING] = [{"key": key_name or "OBS_KEY_F8"}]
    return hotkey_label(settings.get(HOTKEY_SETTING))


def install(key_name):
    if not OVERLAY.is_file() or not SCRIPT.is_file():
        raise SystemExit(f"Missing overlay files next to {Path(__file__).name}.")
    if obs_is_running():
        raise SystemExit("Quit OBS first. It saves the scene file when it closes, and that would undo this install.")

    configs = config_dirs()
    if not configs:
        raise SystemExit("OBS has no settings yet. Open OBS once, quit it, and run this again.")

    config_dir = configs[0]
    collection_name, path = scene_path(config_dir)
    if not path.is_file():
        raise SystemExit(f"Scene collection file is missing: {path}")

    width, height = canvas_size(config_dir)
    collection = json.loads(path.read_text())
    sources = collection.setdefault("sources", [])
    prev_ver = next((source.get("prev_ver", 0) for source in sources), 0) or 553648128

    source = find_source(collection)
    if source is None:
        source = browser_source(SOURCE_NAME, str(uuid.uuid4()), width, height, prev_ver)
        sources.append(source)
    else:
        configure_source(source, width, height)

    scenes = [entry for entry in sources if entry.get("id") == "scene"]
    if not scenes:
        raise SystemExit("This scene collection has no scenes yet. Open OBS once, then run this again.")
    for scene in scenes:
        place_on_scene(scene, source, width, height)

    hotkey = install_script(collection, source["name"], key_name)

    backup = path.with_suffix(path.suffix + ".meow-backup")
    shutil.copy2(path, backup)
    path.write_text(json.dumps(collection, indent="\t") + "\n")

    where = "Flatpak" if ".var/app/com.obsproject.Studio" in str(config_dir) else "the system OBS config"
    print(f"Installed into {where}, scene collection {collection_name}.")
    print(f"Browser source: {source['name']}")
    print(f"Hotkey: {hotkey}")
    print("Opening OBS. The kittens play once as it loads, then again when you press the hotkey.")
    launch_obs(config_dir)


def launch_obs(config_dir):
    if ".var/app/com.obsproject.Studio" in str(config_dir):
        command = ["flatpak", "run", "com.obsproject.Studio"]
    else:
        command = ["obs"]
    subprocess.Popen(command, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description="Install the Meow for E-Kittens overlay into OBS.")
    parser.add_argument("--key", help="Hotkey to bind, such as F8 or K. Default is F8 when none is saved.")
    args = parser.parse_args()
    install(obs_key(args.key) if args.key else None)


if __name__ == "__main__":
    main()
