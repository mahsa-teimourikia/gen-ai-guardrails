from pathlib import Path

from scripts.validate_links import validate_links


def test_curriculum_structure():
    root = Path(__file__).parent.parent
    curriculum = root / "curriculum"
    for track in ("beginner", "intermediate", "advanced"):
        assert (curriculum / track / "README.md").is_file()


def test_every_course_has_readme_with_title():
    root = Path(__file__).parent.parent / "curriculum"
    for course in root.glob("*/*-*/"):
        readme = course / "README.md"
        assert readme.is_file(), course
        assert readme.read_text(encoding="utf-8").splitlines()[0].startswith("# ")


def test_internal_links_are_valid():
    root = Path(__file__).parent.parent
    assert validate_links(root) == []
