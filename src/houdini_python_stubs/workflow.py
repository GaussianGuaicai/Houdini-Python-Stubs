from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._houdini_env import discover_houdini_installs, resolve_houdini_install
from .doc_validation import validate_stub_set
from .hapi_pyi_gen_standalone import generate_hapi_stubs
from .hou_pyi_update import generate_hou_stubs
from .pdg_pyi_gen_standalone import generate_pdg_stubs


MODULE_GENERATORS = {
    "hou": lambda *, install, output_dir, tmp_root: generate_hou_stubs(
        hfs=str(install.hfs),
        tmp_dir=str(tmp_root / "hou"),
        output_dir=str(output_dir),
    ),
    "pdg": lambda *, install, output_dir, tmp_root: generate_pdg_stubs(
        hfs=str(install.hfs),
        output_dir=str(output_dir),
    ),
    "hapi": lambda *, install, output_dir, tmp_root: generate_hapi_stubs(
        hfs=str(install.hfs),
        output_dir=str(output_dir),
    ),
}


def run_workflow(
    *,
    version: str | None = None,
    hfs: str | None = None,
    modules: list[str] | None = None,
    output_root: str | Path = "output",
    validate_docs: bool = True,
) -> dict:
    install = resolve_houdini_install(version=version, hfs=hfs)
    selected_modules = modules or ["hou", "pdg", "hapi"]

    output_root_path = Path(output_root)
    version_output_dir = output_root_path / install.version
    tmp_root = Path("tmp") / install.version
    version_output_dir.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)

    for module_name in selected_modules:
        MODULE_GENERATORS[module_name](
            install=install,
            output_dir=version_output_dir,
            tmp_root=tmp_root,
        )

    validation_reports = None
    if validate_docs:
        validation_reports = validate_stub_set(
            install=install,
            output_dir=version_output_dir,
            modules=selected_modules,
        )

    summary = {
        "houdini_version": install.version,
        "docs_version": install.docs_version,
        "hfs": str(install.hfs),
        "output_dir": str(version_output_dir.resolve()),
        "modules": selected_modules,
        "validation": validation_reports,
    }

    summary_path = version_output_dir / "workflow_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Houdini pyi stubs for a specific installed version and validate against docs"
    )
    parser.add_argument("--version", help="Houdini version such as 21.0.512 or 21.0")
    parser.add_argument("--hfs", help="Explicit Houdini install path (HFS)")
    parser.add_argument(
        "--modules",
        default="hou,pdg,hapi",
        help="Comma-separated module list to generate",
    )
    parser.add_argument(
        "--output-root",
        default="output",
        help="Root folder for per-version generated outputs",
    )
    parser.add_argument(
        "--skip-doc-validation",
        action="store_true",
        help="Only generate stubs and skip SideFX docs validation",
    )
    parser.add_argument(
        "--list-installed",
        action="store_true",
        help="List discovered Houdini installs and exit",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    if args.list_installed:
        installs = [
            {"version": install.version, "hfs": str(install.hfs), "python_lib_dir": str(install.python_lib_dir)}
            for install in discover_houdini_installs()
        ]
        print(json.dumps(installs, indent=2, ensure_ascii=False))
        return

    modules = [value.strip() for value in args.modules.split(",") if value.strip()]
    summary = run_workflow(
        version=args.version,
        hfs=args.hfs,
        modules=modules,
        output_root=args.output_root,
        validate_docs=not args.skip_doc_validation,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
