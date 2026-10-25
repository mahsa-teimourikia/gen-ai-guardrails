from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).parents[1]


def test_every_curriculum_notebook_executes():
    notebooks = sorted(ROOT.glob("curriculum/**/*.ipynb"))
    assert notebooks
    for notebook_path in notebooks:
        notebook = nbformat.read(notebook_path, as_version=4)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                assert cell.get("outputs") == [], notebook_path
                assert cell.get("execution_count") is None, notebook_path
        NotebookClient(
            notebook,
            timeout=120,
            kernel_name="python3",
            resources={"metadata": {"path": str(notebook_path.parent)}},
        ).execute()
