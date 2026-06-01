from __future__ import annotations

import argparse
import contextlib
import dataclasses
import glob
import os
import re
import sys
from pathlib import Path
from typing import Iterator, Sequence


DEFAULT_WINDOWS_INSTALL_ROOT = Path("C:/Program Files/Side Effects Software")
VERSION_RE = re.compile(r"Houdini\s+(?P<version>\d+\.\d+(?:\.\d+)?)$")


@dataclasses.dataclass(frozen=True)
class HoudiniInstall:
    version: str
    hfs: Path
    python_lib_dir: Path

    @property
    def docs_version(self) -> str:
        parts = self.version.split(".")
        if len(parts) < 2:
            raise ValueError(f"Unsupported Houdini version format: {self.version}")
        return ".".join(parts[:2])


def normalize_hfs(hfs: str | Path) -> Path:
    return Path(str(hfs).replace("\\", "/")).resolve()


def detect_python_lib_dir(hfs: str | Path) -> Path:
    normalized = normalize_hfs(hfs)
    candidates = sorted(glob.glob(str(normalized / "houdini" / "python3.*libs")))
    if not candidates:
        raise FileNotFoundError(f"Could not find Houdini python libs under HFS={normalized}")
    return Path(candidates[-1]).resolve()


def detect_hou_binary(hfs: str | Path) -> Path:
    lib_dir = detect_python_lib_dir(hfs)
    for name in ("_hou.pyd", "_hou.so"):
        candidate = lib_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find _hou binary in {lib_dir}")


def parse_install_version(hfs: str | Path) -> str:
    name = normalize_hfs(hfs).name
    match = VERSION_RE.search(name)
    if not match:
        raise ValueError(f"Could not parse Houdini version from install path: {hfs}")
    return match.group("version")


def build_install(hfs: str | Path) -> HoudiniInstall:
    normalized = normalize_hfs(hfs)
    return HoudiniInstall(
        version=parse_install_version(normalized),
        hfs=normalized,
        python_lib_dir=detect_python_lib_dir(normalized),
    )


def discover_houdini_installs(search_roots: Sequence[Path] | None = None) -> list[HoudiniInstall]:
    roots = list(search_roots or [DEFAULT_WINDOWS_INSTALL_ROOT])
    installs: list[HoudiniInstall] = []
    seen: set[Path] = set()

    env_hfs = os.environ.get("HFS")
    if env_hfs:
        candidate = normalize_hfs(env_hfs)
        if candidate not in seen and candidate.exists():
            with contextlib.suppress(Exception):
                installs.append(build_install(candidate))
                seen.add(candidate)

    for root in roots:
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if child in seen:
                continue
            if not VERSION_RE.search(child.name):
                continue
            with contextlib.suppress(Exception):
                installs.append(build_install(child))
                seen.add(child)

    installs.sort(key=lambda item: tuple(int(part) for part in item.version.split(".")))
    return installs


def resolve_houdini_install(version: str | None = None, hfs: str | Path | None = None) -> HoudiniInstall:
    if hfs:
        install = build_install(hfs)
        if version and not install.version.startswith(version):
            raise ValueError(
                f"Requested version {version} does not match resolved install {install.version} at {install.hfs}"
            )
        return install

    installs = discover_houdini_installs()
    if not installs:
        raise FileNotFoundError(
            f"No Houdini installs were found under {DEFAULT_WINDOWS_INSTALL_ROOT}"
        )

    if not version:
        return installs[-1]

    exact = [install for install in installs if install.version == version]
    if exact:
        return exact[-1]

    prefix = [install for install in installs if install.version.startswith(f"{version}.")]
    if prefix:
        return prefix[-1]

    docs_match = [install for install in installs if install.docs_version == version]
    if docs_match:
        return docs_match[-1]

    available = ", ".join(install.version for install in installs)
    raise ValueError(f"Could not find Houdini version {version}. Available installs: {available}")


@contextlib.contextmanager
def houdini_runtime_environment(install: HoudiniInstall) -> Iterator[None]:
    previous_hfs = os.environ.get("HFS")
    previous_hhp = os.environ.get("HHP")
    old_dlopen_flags = None
    dll_handle = None
    added_sys_path = False
    dll_dir = install.hfs / "bin"

    os.environ["HFS"] = str(install.hfs)
    os.environ["HHP"] = str(install.python_lib_dir)

    if hasattr(sys, "setdlopenflags"):
        old_dlopen_flags = sys.getdlopenflags()
        sys.setdlopenflags(old_dlopen_flags | os.RTLD_GLOBAL)

    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        dll_handle = os.add_dll_directory(str(dll_dir))

    if str(install.python_lib_dir) not in sys.path:
        sys.path.append(str(install.python_lib_dir))
        added_sys_path = True

    try:
        yield
    finally:
        if added_sys_path:
            with contextlib.suppress(ValueError):
                sys.path.remove(str(install.python_lib_dir))

        if dll_handle is not None:
            dll_handle.close()

        if hasattr(sys, "setdlopenflags") and old_dlopen_flags is not None:
            sys.setdlopenflags(old_dlopen_flags)

        if previous_hfs is None:
            os.environ.pop("HFS", None)
        else:
            os.environ["HFS"] = previous_hfs

        if previous_hhp is None:
            os.environ.pop("HHP", None)
        else:
            os.environ["HHP"] = previous_hhp


def add_shared_cli_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--version", help="Houdini version such as 21.0.512 or 21.0")
    parser.add_argument("--hfs", help="Explicit Houdini install path (HFS)")
    return parser
