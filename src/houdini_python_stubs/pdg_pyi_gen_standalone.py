from __future__ import annotations

import argparse
from pathlib import Path

from ._houdini_env import add_shared_cli_arguments
from ._stubgen_utils import generate_pybind11_stubs


def generate_pdg_stubs(output_dir: str | Path, version: str | None = None, hfs: str | None = None) -> Path:
    generate_pybind11_stubs(
        module_names=["_pdg", "pdg"],
        output_dir=output_dir,
        version=version,
        hfs=hfs,
    )
    return Path(output_dir) / "pdg"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate pdg pyi stubs for a Houdini install")
    add_shared_cli_arguments(parser)
    parser.add_argument("--output-dir", default="output", help="Directory to write pdg stubs into")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    generate_pdg_stubs(output_dir=args.output_dir, version=args.version, hfs=args.hfs)


if __name__ == "__main__":
    main()
