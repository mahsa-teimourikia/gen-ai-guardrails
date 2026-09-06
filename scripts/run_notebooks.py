"""Execute selected notebooks and reject committed execution artifacts."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).parents[1]


def changed_notebooks(base: str) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD", "--", "*.ipynb"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / name for name in result.stdout.splitlines() if name.endswith(".ipynb")]


def all_notebooks() -> list[Path]:
    return sorted(ROOT.glob("curriculum/**/*.ipynb"))


def selected_notebooks(base: str | None, paths: list[str]) -> list[Path]:
    if paths:
        return [Path(path).resolve() for path in paths]
    if base:
        return changed_notebooks(base)
    return all_notebooks()


def stale_cells(notebook) -> list[str]:
    stale: list[str] = []
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        if cell.get("outputs") or cell.get("execution_count") is not None:
            stale.append(str(index))
    return stale


def run_one(path: Path) -> tuple[str, str]:
    label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    try:
        notebook = nbformat.read(path, as_version=4)
        stale = stale_cells(notebook)
        if stale:
            return "FAIL", f"committed outputs/execution counts in cells {', '.join(stale)}"
        NotebookClient(
            notebook,
            timeout=120,
            kernel_name="python3",
            resources={"metadata": {"path": str(path.parent)}},
        ).execute()
    except Exception as error:
        return "FAIL", f"{type(error).__name__}: {error}"
    return "PASS", "executed"


def print_table(results: list[tuple[str, str, str]]) -> None:
    print("| Notebook | Status | Details |")
    print("| --- | --- | --- |")
    for path, status, details in results:
        print(f"| `{path}` | {status} | {details} |")


def append_summary(results: list[tuple[str, str, str]]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as stream:
        stream.write("\n## Notebook execution\n\n")
        stream.write("| Notebook | Status | Details |\n| --- | --- | --- |\n")
        for path, status, details in results:
            stream.write(f"| `{path}` | {status} | {details} |\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Git ref used to select changed notebooks")
    parser.add_argument("paths", nargs="*", help="Notebook paths to execute")
    arguments = parser.parse_args()
    paths = selected_notebooks(arguments.base, arguments.paths)
    if not paths:
        print("No notebooks changed")
        return 0

    results = []
    for path in paths:
        label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        if not path.is_file():
            results.append((label, "FAIL", "file not found"))
            continue
        status, details = run_one(path)
        results.append((label, status, details))
    print_table(results)
    append_summary(results)
    return 1 if any(status == "FAIL" for _, status, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
