#!/usr/bin/env python3
"""Verify a .glb avatar carries the viseme morph targets ZAI needs.

Ready Player Me will happily return a valid, good-looking GLB with NO morph
targets if the download URL is wrong. The model then loads fine and the mouth
never moves, which looks exactly like an application bug. Run this first.

Usage:
    python ops/check_avatar.py frontend/static/assets/avatar.glb
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

# What app/../avatar3d.js drives. Oculus visemes are preferred; ARKit shapes
# are used as fallbacks for a few of them.
REQUIRED_OCULUS = [
    "viseme_sil", "viseme_PP", "viseme_FF", "viseme_TH", "viseme_DD",
    "viseme_kk", "viseme_CH", "viseme_SS", "viseme_nn", "viseme_RR",
    "viseme_aa", "viseme_E", "viseme_I", "viseme_O", "viseme_U",
]
# Slots the ARKit recipe path needs (see avatar3d.js RECIPES).
ARKIT_FALLBACK = ["jawOpen", "mouthFunnel", "mouthPucker", "mouthClose",
                  "mouthStretch_L", "mouthStretchLeft",
                  "mouthPress_L", "mouthPressLeft"]
BLINK = ["eyeBlink_L", "eyeBlink_R", "eyeBlinkLeft", "eyeBlinkRight", "eyesClosed"]

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def read_glb_json(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        # A plain .gltf file is JSON already.
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise SystemExit(f"{RED}Not a glTF/GLB file: {path}{RESET}") from exc

    _magic, version, _length = struct.unpack_from("<4sII", data, 0)
    if version != 2:
        raise SystemExit(f"{RED}Unsupported glTF version {version} (need 2){RESET}")

    offset = 12
    while offset < len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        if chunk_type == 0x4E4F534A:  # 'JSON'
            return json.loads(data[offset:offset + chunk_len].decode("utf-8"))
        offset += chunk_len
    raise SystemExit(f"{RED}No JSON chunk found in {path}{RESET}")


def collect_target_names(gltf: dict) -> dict[str, list[str]]:
    """Morph target names, per mesh. RPM splits the face across several meshes."""
    per_mesh: dict[str, list[str]] = {}
    for mesh in gltf.get("meshes", []):
        names = mesh.get("extras", {}).get("targetNames") or []
        if not names:
            # Some exporters put targetNames on the primitive instead.
            for prim in mesh.get("primitives", []):
                names = prim.get("extras", {}).get("targetNames") or names
        if names:
            per_mesh[mesh.get("name", "<unnamed>")] = list(names)
    return per_mesh


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"{RED}File not found: {path}{RESET}")
        return 1

    size_mb = path.stat().st_size / 1_048_576
    gltf = read_glb_json(path)
    per_mesh = collect_target_names(gltf)
    all_names = {n for names in per_mesh.values() for n in names}

    print(f"\n  File     {path}")
    print(f"  Size     {size_mb:.1f} MB")
    print(f"  Meshes   {len(gltf.get('meshes', []))}")
    print(f"  Morphs   {len(all_names)} distinct target names")

    # Compressed glTF needs extra decoders in the browser. Without them
    # GLTFLoader throws on parse and it looks like a missing file.
    required = gltf.get("extensionsRequired", [])
    used = gltf.get("extensionsUsed", [])
    if required:
        print(f"  Requires {', '.join(required)}")
    elif used:
        print(f"{DIM}  Uses     {', '.join(used)}{RESET}")
    print()

    KNOWN = {
        "KHR_draco_mesh_compression": "Draco (decoder vendored)",
        "EXT_meshopt_compression": "meshopt (decoder vendored)",
        "KHR_texture_basisu": "KTX2/Basis (transcoder vendored)",
    }
    unknown = [e for e in required if e not in KNOWN and not e.startswith("KHR_materials")
               and e not in ("KHR_texture_transform", "KHR_mesh_quantization")]
    if unknown:
        print(f"{YELLOW}  NOTE — unrecognised required extension(s): "
              f"{', '.join(unknown)}{RESET}")
        print(f"{DIM}  These may fail to load in the browser.{RESET}\n")

    if not all_names:
        print(f"{RED}  FAIL — this GLB contains no morph targets at all.{RESET}")
        print(f"{DIM}  The mouth cannot move. Re-download with the morphTargets")
        print(f"  parameter, for example:")
        print(f"    https://models.readyplayer.me/<id>.glb?morphTargets=Oculus%20Visemes{RESET}\n")
        return 1

    for mesh_name, names in per_mesh.items():
        visemes = [n for n in names if n.startswith("viseme_")]
        print(f"{DIM}  {mesh_name}: {len(names)} targets"
              f"{f', {len(visemes)} visemes' if visemes else ''}{RESET}")
    print()

    found = [v for v in REQUIRED_OCULUS if v in all_names]
    missing = [v for v in REQUIRED_OCULUS if v not in all_names]
    arkit = [a for a in ARKIT_FALLBACK if a in all_names]
    blink = [b for b in BLINK if b in all_names]

    if len(found) >= 12:
        print(f"{GREEN}  PASS — {len(found)}/15 Oculus visemes present. "
              f"Lip sync will work.{RESET}")
    elif arkit:
        print(f"{GREEN}  PASS — ARKit rig detected ({len(arkit)} usable shapes). "
              f"Lip sync will work via viseme recipes.{RESET}")
        print(f"{DIM}  Oculus visemes would be slightly crisper, but this is fine.{RESET}")
    else:
        print(f"{RED}  FAIL — no usable viseme targets "
              f"({len(found)}/15 Oculus, no ARKit fallback).{RESET}")
        print(f"{DIM}  Re-download with ?morphTargets=Oculus%20Visemes{RESET}")

    if missing and found:
        print(f"{DIM}  Missing: {', '.join(missing)}{RESET}")
    print(f"  Blink    {GREEN + ', '.join(blink) + RESET if blink else YELLOW + 'none — avatar will not blink' + RESET}")

    if size_mb > 12:
        print(f"{YELLOW}  NOTE — {size_mb:.1f} MB is large for a browser demo. "
              f"Add &textureSizeLimit=1024 to the download URL.{RESET}")

    print()
    return 0 if (len(found) >= 12 or arkit) else 1


if __name__ == "__main__":
    sys.exit(main())