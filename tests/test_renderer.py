from pathlib import Path
from folderdump.core import (
    render_plain, render_tree, render_markdown,
    render_json, render_csv, render_dot
)


def sample_items():
    return [
        (Path("dirA"), True, 1),
        (Path("dirA/file1.txt"), False, 2),
        (Path("dirB"), True, 1),
    ]


def test_render_plain(tmp_path):
    text = render_plain(tmp_path, sample_items(), absolute=False)
    assert "dirA/" in text
    assert "file1.txt" in text


def test_render_tree():
    text = render_tree(sample_items())
    assert "." in text
    assert "dirA" in text


def test_render_markdown():
    text = render_markdown("hello")
    assert text.startswith("```")
    assert text.endswith("```")


def test_render_json():
    text = render_json(sample_items())
    assert "dirA" in text
    assert text.strip().startswith("{") or text.strip().startswith("[")


def test_render_csv(tmp_path):
    text = render_csv(tmp_path, sample_items())
    assert "path,is_dir,depth" in text


def test_render_dot():
    text = render_dot(sample_items())
    assert "digraph G" in text
