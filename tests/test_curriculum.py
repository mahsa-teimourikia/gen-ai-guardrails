from pathlib import Path
import re

from scripts.validate_links import validate_links


ROOT = Path(__file__).parent.parent
COURSES = sorted(ROOT.glob("curriculum/*/[0-9][0-9]-*/"))


def test_curriculum_structure():
    curriculum = ROOT / "curriculum"
    for track in ("beginner", "intermediate", "advanced"):
        assert (curriculum / track / "README.md").is_file()
    assert len(COURSES) == 8


def test_every_course_has_complete_published_artifacts():
    required_sections = {
        "**Level:**",
        "**Estimated time:**",
        "**Prerequisites:**",
        "**Notebook:**",
        "## Learning objectives",
        "## Exercises",
        "## Setup",
        "## Where this fits",
    }
    for course in COURSES:
        readme = course / "README.md"
        assert readme.is_file(), course
        text = readme.read_text(encoding="utf-8")
        assert text.splitlines()[0].startswith("# ")
        assert all(section in text for section in required_sections), course
        assert len(list(course.glob("*.ipynb"))) == 1, course
        assert len(list(course.glob("*_lab.py"))) == 1, course


def test_learning_hub_covers_every_course_and_reusable_lab():
    hub = (ROOT / "app/page.tsx").read_text(encoding="utf-8")
    assert len(re.findall(r'^\s+id:\s*"[bia]\d+",', hub, re.MULTILINE)) == 8
    assert len(re.findall(r'^\s+question:\s*"', hub, re.MULTILINE)) == 24
    for course in COURSES:
        relative = course.relative_to(ROOT).as_posix().rstrip("/")
        assert f"{relative}/README.md" in hub
        notebook = next(course.glob("*.ipynb")).relative_to(ROOT).as_posix()
        lab = next(course.glob("*_lab.py")).relative_to(ROOT).as_posix()
        assert notebook in hub
        assert lab in hub


def test_internal_links_are_valid():
    assert validate_links(ROOT) == []
