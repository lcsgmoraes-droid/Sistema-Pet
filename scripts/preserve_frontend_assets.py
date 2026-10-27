#!/usr/bin/env python3
"""Keep recently retired public assets available to already-open browser tabs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import time


MANIFEST_NAME = ".frontend-assets.json"
DAY_SECONDS = 24 * 60 * 60


def _is_link(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def _public_asset(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and "\\" not in name
        and ":" not in name
        and all(
            part not in ("", ".", "..") and not part.startswith(".")
            for part in name.split("/")
        )
        and path.suffix.lower() not in (".html", ".htm", ".map")
    )


def _asset_files(dist: Path) -> dict[str, Path]:
    assets = dist / "assets"
    if _is_link(assets):
        raise ValueError("Diretorio assets nao pode ser um link")
    if not assets.exists():
        return {}
    if not assets.is_dir():
        raise ValueError("assets precisa ser um diretorio")
    files = {}
    for path in assets.rglob("*"):
        if _is_link(path):
            raise ValueError("Assets nao podem conter links")
        if not path.resolve().is_relative_to(assets.resolve()):
            raise ValueError("Asset fora do diretorio permitido")
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("Assets precisam ser arquivos comuns")
        name = path.relative_to(assets).as_posix()
        if _public_asset(name):
            files[name] = path
    return files


def _read_manifest(
    dist: Path, files: dict[str, Path]
) -> tuple[set[str], dict[str, float]]:
    path = dist / MANIFEST_NAME
    if _is_link(path):
        raise ValueError("Manifesto de assets nao pode ser um link")
    if not path.exists():
        # Before the first compatible deploy every asset belongs to the active build.
        return set(files), {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ValueError("Manifesto de assets invalido")
    current = manifest.get("current")
    retained = manifest.get("retained")
    if not isinstance(current, list) or not isinstance(retained, dict):
        raise ValueError("Manifesto de assets invalido")
    if not all(isinstance(name, str) and _public_asset(name) for name in current):
        raise ValueError("Caminho de asset invalido no manifesto")
    if not all(
        isinstance(name, str)
        and _public_asset(name)
        and isinstance(expiry, (int, float))
        and not isinstance(expiry, bool)
        and math.isfinite(expiry)
        and expiry > 0
        for name, expiry in retained.items()
    ):
        raise ValueError("Retencao de assets invalida no manifesto")
    if set(current) & set(retained):
        raise ValueError("Asset atual nao pode ser tambem herdado")
    return set(current), retained


def preserve_assets(
    current_dist: Path,
    next_dist: Path,
    *,
    keep_days: int = 7,
    now: float | None = None,
) -> dict[str, int]:
    """Prepare a fresh next build; never modify the active or rollback directories."""

    if (
        isinstance(keep_days, bool)
        or not isinstance(keep_days, int)
        or not 1 <= keep_days <= 90
    ):
        raise ValueError("Retencao precisa estar entre 1 e 90 dias")
    if _is_link(current_dist) or _is_link(next_dist):
        raise ValueError("Diretorios de build nao podem ser links")
    current_dist, next_dist = current_dist.resolve(), next_dist.resolve()
    if current_dist.is_relative_to(next_dist) or next_dist.is_relative_to(current_dist):
        raise ValueError("Build atual e proximo precisam de diretorios separados")
    if current_dist.exists() and not current_dist.is_dir():
        raise ValueError("Build atual precisa ser um diretorio")
    if not next_dist.is_dir() or not (next_dist / "index.html").is_file():
        raise ValueError("Proximo build precisa conter index.html")
    if (next_dist / MANIFEST_NAME).exists() or _is_link(next_dist / MANIFEST_NAME):
        raise ValueError("Proximo build ja foi preparado; gere um build limpo")
    timestamp = time.time() if now is None else now
    if not math.isfinite(timestamp) or timestamp <= 0:
        raise ValueError("Horario de retencao invalido")

    old_files = _asset_files(current_dist)
    new_files = _asset_files(next_dist)
    old_current, old_retained = _read_manifest(current_dist, old_files)
    expires_at = timestamp + keep_days * DAY_SECONDS
    retained = {}
    expired = 0
    for name, source in sorted(old_files.items()):
        if name in new_files:
            continue
        expiry = expires_at if name in old_current else old_retained.get(name, 0)
        if expiry <= timestamp:
            expired += 1
            continue
        destination = next_dist / "assets" / name
        if destination.exists():
            raise ValueError("Asset anterior conflita com o proximo build")
        destination.parent.mkdir(parents=True, exist_ok=True)
        # A current build asset always wins. copy2 preserves the old file itself.
        shutil.copy2(source, destination, follow_symlinks=False)
        retained[name] = min(expiry, expires_at)

    manifest = {
        "version": 1,
        "current": sorted(new_files),
        "retained": retained,
    }
    (next_dist / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"current": len(new_files), "preserved": len(retained), "expired": expired}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-dist", required=True, type=Path)
    parser.add_argument("--next-dist", required=True, type=Path)
    parser.add_argument("--keep-days", type=int, default=7)
    args = parser.parse_args()
    try:
        result = preserve_assets(
            args.current_dist, args.next_dist, keep_days=args.keep_days
        )
    except (OSError, ValueError) as error:
        print(f"Falha ao preservar assets do frontend: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"frontend_assets": result, "retention_days": args.keep_days}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
