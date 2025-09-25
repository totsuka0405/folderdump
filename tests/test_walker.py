import os
from pathlib import Path
import tempfile
import shutil

import pytest
from folderdump.core.walker import iter_paths, Stats, SkipLog, CtlFlags


def make_temp_tree(base: Path):
    """テスト用の一時ディレクトリ構造を作成"""
    (base / "dirA").mkdir()
    (base / "dirB").mkdir()
    (base / "dirA" / "subA").mkdir()
    (base / "dirA" / "file1.txt").write_text("hello")
    (base / "dirB" / "file2.txt").write_text("world")


def test_iter_paths_lists_directories_and_files(tmp_path: Path):
    make_temp_tree(tmp_path)

    flags = CtlFlags()
    stats = Stats()
    skiplog = SkipLog()

    items = list(
        iter_paths(
            root=tmp_path,
            max_depth=None,
            follow_symlinks=False,
            includes=[],
            excludes=[],
            dirs_first=True,
            folders_only=False,
            flags=flags,
            skiplog=skiplog,
            stats=stats,
        )
    )

    names = {str(p) for p, is_dir, _ in items}
    assert "dirA" in names
    assert "dirB" in names
    assert "dirA/file1.txt" in names or "dirA\\file1.txt" in names
    assert stats.total > 0
    assert skiplog.count() == 0
