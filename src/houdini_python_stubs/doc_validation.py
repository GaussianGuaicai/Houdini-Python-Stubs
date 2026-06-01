from __future__ import annotations

import argparse
import contextlib
import json
import re
import socket
import subprocess
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

from ._houdini_env import HoudiniInstall, add_shared_cli_arguments, resolve_houdini_install


LOCAL_DOC_PATHS = {
    "hou": "hom/hou/index.html",
    "pdg": "tops/pdg/index.html",
    "hapi": "hapi/index.html",
}


class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.hrefs.append(value)


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "houdini-python-stubs-validator/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def running_local_help_service(
    install: HoudiniInstall,
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
    startup_timeout: float = 30.0,
):
    service_port = port or find_free_port()
    hhelp_exe = install.hfs / "bin" / "hhelp.exe"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [str(hhelp_exe), "serve", "-h", host, "-p", str(service_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    service_root = f"http://{host}:{service_port}/"
    deadline = time.time() + startup_timeout
    last_error: Exception | None = None
    try:
        while time.time() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Local Houdini Help service exited early with code {process.returncode}")
            try:
                fetch_text(service_root)
                yield service_root
                return
            except Exception as exc:  # pragma: no cover - polling path
                last_error = exc
                time.sleep(1.0)
        raise RuntimeError(
            f"Timed out waiting for local Houdini Help service at {service_root}: {last_error}"
        )
    finally:
        with contextlib.suppress(Exception):
            process.terminate()
        with contextlib.suppress(Exception):
            process.wait(timeout=5)
        if process.poll() is None:
            with contextlib.suppress(Exception):
                process.kill()


def documented_symbols(module_name: str, service_root: str) -> tuple[str, set[str]]:
    doc_index_url = urljoin(service_root, LOCAL_DOC_PATHS[module_name])
    html = fetch_text(doc_index_url)
    parser = AnchorCollector()
    parser.feed(html)

    module_path = {
        "hou": "/hom/hou/",
        "pdg": "/tops/pdg/",
        "hapi": "/hapi/",
    }[module_name]
    symbol_re = re.compile(re.escape(module_path) + r"(?P<name>[^/#?]+)\.html$")

    names: set[str] = set()
    for href in parser.hrefs:
        absolute_href = urljoin(doc_index_url, href)
        match = symbol_re.search(urlparse(absolute_href).path)
        if not match:
            continue
        name = match.group("name")
        if name == "index" or name.startswith("_"):
            continue
        names.add(name)

    return doc_index_url, names


def stub_symbols(stub_path: str | Path) -> set[str]:
    names: set[str] = set()
    top_level_patterns = [
        re.compile(r"^class\s+(?P<name>[A-Za-z_]\w*)\b", re.MULTILINE),
        re.compile(r"^def\s+(?P<name>[A-Za-z_]\w*)\s*\(", re.MULTILINE),
        re.compile(r"^(?P<name>[A-Za-z_]\w*)\s*:\s*.*$", re.MULTILINE),
        re.compile(r"^from\s+[.\w]+\s+import\s+(?P<imports>.+)$", re.MULTILINE),
        re.compile(r"^import\s+(?P<imports>[A-Za-z_]\w*(?:\s+as\s+[A-Za-z_]\w*)?(?:\s*,\s*[A-Za-z_]\w*(?:\s+as\s+[A-Za-z_]\w*)?)*)$", re.MULTILINE),
    ]
    path = Path(stub_path)
    if path.is_file():
        files = [path]
    else:
        init_file = path / "__init__.pyi"
        files = [init_file] if init_file.exists() else sorted(path.rglob("*.pyi"))
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        for pattern in top_level_patterns:
            for match in pattern.finditer(text):
                if "name" in match.groupdict():
                    name = match.group("name")
                    if not name.startswith("_"):
                        names.add(name)
                    continue

                imports = match.group("imports")
                for raw_part in imports.split(","):
                    part = raw_part.split("#", maxsplit=1)[0].strip()
                    if not part or part == "*":
                        continue
                    alias = part.split(" as ")[-1].strip()
                    if alias and not alias.startswith("_"):
                        names.add(alias)

        all_match = re.search(r"__all__\s*=\s*\[(?P<body>.*?)\]", text, re.DOTALL)
        if all_match:
            body = all_match.group("body")
            for quoted in re.finditer(r"['\"](?P<name>[^'\"]+)['\"]", body):
                name = quoted.group("name")
                if name and not name.startswith("_"):
                    names.add(name)
    return names


def summarize_validation(module_name: str, stub_path: str | Path, docs_version: str, service_root: str) -> dict:
    doc_index_url, docs_names = documented_symbols(module_name, service_root)
    stub_names = stub_symbols(stub_path)

    missing = sorted(docs_names - stub_names)
    extras = sorted(stub_names - docs_names)
    coverage = 1.0 if not docs_names else (len(docs_names) - len(missing)) / len(docs_names)

    return {
        "module": module_name,
        "stub_path": str(Path(stub_path).resolve()),
        "doc_index_url": doc_index_url,
        "docs_version": docs_version,
        "documented_symbol_count": len(docs_names),
        "stub_symbol_count": len(stub_names),
        "coverage_ratio": round(coverage, 4),
        "basically_consistent": coverage >= 0.85,
        "missing_from_stub": missing,
        "extra_in_stub": extras,
    }


def resolve_stub_path(output_dir: str | Path, module_name: str) -> Path:
    output_path = Path(output_dir)
    candidates = [
        output_path / f"{module_name}.pyi",
        output_path / module_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find generated stub for module {module_name} under {output_path}")


def validate_stub_set(
    *,
    install: HoudiniInstall,
    output_dir: str | Path,
    modules: Iterable[str],
) -> dict[str, dict]:
    output_path = Path(output_dir)
    reports: dict[str, dict] = {}
    with running_local_help_service(install) as service_root:
        for module_name in modules:
            stub_path = resolve_stub_path(output_path, module_name)
            reports[module_name] = summarize_validation(
                module_name,
                stub_path,
                install.docs_version,
                service_root,
            )

    report_dir = output_path / "validation"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "houdini_version": install.version,
                "docs_version": install.docs_version,
                "reports": reports,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return reports


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate generated stubs against SideFX docs")
    add_shared_cli_arguments(parser)
    parser.add_argument("--output-dir", required=True, help="Directory containing generated pyi files")
    parser.add_argument(
        "--modules",
        default="hou,pdg,hapi",
        help="Comma-separated module list to validate",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    install = resolve_houdini_install(version=args.version, hfs=args.hfs)
    modules = [value.strip() for value in args.modules.split(",") if value.strip()]
    reports = validate_stub_set(
        install=install,
        output_dir=args.output_dir,
        modules=modules,
    )
    print(
        json.dumps(
            {"houdini_version": install.version, "docs_version": install.docs_version, "reports": reports},
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
