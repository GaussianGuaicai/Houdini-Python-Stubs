# Houdini-Python-Stubs

Generate Python type stubs for `hou`, `pdg`, and `hapi` from a specific Houdini install on the current machine, then compare the generated stubs against the matching documentation served by that same local Houdini install.

## What changed

The workflow is now version-aware instead of relying on hardcoded `HFS` / `HHP` edits inside standalone scripts:

- It discovers installed Houdini versions from the current system.
- It can target an exact install such as `21.0.512` or a docs family such as `20.5`.
- It generates `hou`, `pdg`, and `hapi` stubs into a per-version output folder.
- It validates symbol coverage against the corresponding local Houdini Help service for the same install.

## Quick start

List detected installs:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m houdini_python_stubs.workflow --list-installed
```

Generate all stubs for a specific installed version and validate them against the matching docs:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m houdini_python_stubs.workflow --version 21.0.512
```

Generate only `hou` and `pdg`:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m houdini_python_stubs.workflow --version 20.5.684 --modules hou,pdg
```

Point to an explicit install path:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m houdini_python_stubs.workflow --hfs "C:\Program Files\Side Effects Software\Houdini 19.5.805"
```

Skip docs validation:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m houdini_python_stubs.workflow --version 21.0.512 --skip-doc-validation
```

## Output layout

For `--version 21.0.512`, the workflow writes to:

```text
output/
  21.0.512/
    hou.pyi
    pdg.pyi
    _pdg.pyi
    hapi.pyi
    workflow_summary.json
    validation/
      report.json
```

Intermediate files are written under `tmp/<version>/`.

## Validation behavior

Validation currently checks top-level API symbol coverage between generated stubs and the local Houdini Help service started from the same install:

- `hou` uses `/hom/hou/index.html`
- `pdg` uses `/tops/pdg/index.html`
- `hapi` uses `/hapi/index.html`

The validator launches `hhelp serve` on a temporary localhost port, fetches docs only from that local service, and shuts the service down when validation finishes.

The generated report includes:

- documented symbol count
- stub symbol count
- coverage ratio
- missing symbols from the stub
- extra symbols present in the stub

`basically_consistent` is currently treated as `coverage_ratio >= 0.85`. This is a basic consistency check for API surface coverage, not a full semantic signature verifier.

## Low-level entrypoints

If you only want one generator:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m houdini_python_stubs.hou_pyi_update --hfs "C:\Program Files\Side Effects Software\Houdini 21.0.512" --output-dir output\21.0.512 --tmp-dir tmp\21.0.512\hou
.\.venv\Scripts\python.exe -m houdini_python_stubs.pdg_pyi_gen_standalone --hfs "C:\Program Files\Side Effects Software\Houdini 21.0.512" --output-dir output\21.0.512
.\.venv\Scripts\python.exe -m houdini_python_stubs.hapi_pyi_gen_standalone --hfs "C:\Program Files\Side Effects Software\Houdini 21.0.512" --output-dir output\21.0.512
.\.venv\Scripts\python.exe -m houdini_python_stubs.doc_validation --version 21.0.512 --output-dir output\21.0.512
```
