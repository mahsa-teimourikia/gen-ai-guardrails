"""Validate relative Markdown links and quiz source paths."""

from pathlib import Path
import re


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)\)")
QUIZ_SOURCE = re.compile(r'source\s*:\s*\{[^}]*?url:\s*"([^"]+)"', re.DOTALL)
EXCLUDED = {".git", ".venv", "node_modules"}


def validate_links(root: Path) -> list[str]:
    broken: list[str] = []
    for path in root.rglob("*.md"):
        if any(part in EXCLUDED for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for link in MARKDOWN_LINK.findall(text):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            target = link.split("#", 1)[0] or "."
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(root)} -> {link}")

    quiz_path = root / "quiz" / "questions.js"
    if quiz_path.exists():
        for url in QUIZ_SOURCE.findall(quiz_path.read_text(encoding="utf-8")):
            if url.startswith(("http://", "https://", "mailto:")):
                continue
            target = url.split("#", 1)[0]
            if not (root / target).exists():
                broken.append(f"quiz/questions.js -> {url}")
    return broken


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    broken = validate_links(root)
    if broken:
        print("Broken links:")
        print("\n".join(f"- {item}" for item in broken))
        return 1
    print("All relative Markdown and quiz source links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
