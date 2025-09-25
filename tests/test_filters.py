from pathlib import Path
from folderdump.core import should_keep, read_gitignore


def test_should_keep_includes_and_excludes():
    rel = Path("file.txt")
    assert should_keep(rel, False, includes=["*.txt"], excludes=[]) is True
    assert should_keep(rel, False, includes=["*.md"], excludes=[]) is False
    assert should_keep(rel, False, includes=[], excludes=["*.txt"]) is False


def test_read_gitignore(tmp_path: Path):
    gi = tmp_path / ".gitignore"
    gi.write_text("*.log\n/build/\n")
    patterns = read_gitignore(tmp_path)
    assert "*.log" in patterns
    assert "build" in "".join(patterns)
