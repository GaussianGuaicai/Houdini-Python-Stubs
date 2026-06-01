from __future__ import annotations

import re
import sys
from pathlib import Path

from ._houdini_env import houdini_runtime_environment, resolve_houdini_install

try:
    import pybind11_stubgen as stubgen
except ModuleNotFoundError:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(REPO_ROOT / "submodules" / "pybind11-stubgen"))
    import pybind11_stubgen as stubgen


def regex(pattern_str: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern_str)
    except re.error as exc:
        raise ValueError(f"Invalid REGEX pattern: {exc}") from exc


def regex_colon_path(regex_path: str) -> tuple[re.Pattern[str], str]:
    pattern_str, path = regex_path.rsplit(":", maxsplit=1)
    if any(not part.isidentifier() for part in path.split(".")):
        raise ValueError(f"Invalid PATH: {path}")
    return regex(pattern_str), path


ENUM_CLASS_LOCATIONS = [
    regex_colon_path(value)
    for value in (
        "workItemState:_pdg",
        "attribSaveType:_pdg",
        "dirtyHandlerType:_pdg",
        "cookType:_pdg",
        "attribErrorLevel:_pdg",
        "attribOverwrite:_pdg",
        "attribType:_pdg",
        "attribMatchType:_pdg",
        "pathMapMatchType:_pdg",
        "attribCollisionStrategy:_pdg",
        "fileTransferType:_pdg",
    )
]


def generate_pybind11_stubs(
    *,
    module_names: list[str],
    output_dir: str | Path,
    version: str | None = None,
    hfs: str | None = None,
) -> Path:
    install = resolve_houdini_install(version=version, hfs=hfs)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with houdini_runtime_environment(install):
        import hou  # noqa: F401

        for module_name in module_names:
            stubgen.main(
                module_name=module_name,
                output_dir=str(output_path),
                enum_class_locations=ENUM_CLASS_LOCATIONS,
            )

    return output_path
