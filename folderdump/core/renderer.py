# folderdump/core/renderer.py
"""
出力レンダリング
- plain, tree, markdown, json, csv, dot
"""

import json
import csv
from pathlib import Path
from typing import List, Tuple, Dict


def render_plain(root: Path, items: List[Tuple[Path, bool, int]], absolute: bool) -> str:
    """plain: 単純なリスト形式"""
    lines = []
    base = root.resolve()
    lines.append(str(base if absolute else Path(".")))
    for rel, is_dir, _ in items:
        p = (base / rel) if absolute else rel
        s = str(p) + ("/" if is_dir else "")
        lines.append(s)
    return "\n".join(lines)


def render_tree(items: List[Tuple[Path, bool, int]]) -> str:
    """tree: 疑似 tree コマンド形式"""
    items_sorted = sorted(items, key=lambda x: tuple(x[0].parts))
    from collections import defaultdict
    children = defaultdict(list)

    for rel, is_dir, _ in items_sorted:
        parent = Path(*rel.parts[:-1]) if len(rel.parts) > 1 else Path("")
        children[str(parent)].append((rel, is_dir))

    lines = ["."]
    def draw_dir(parent: Path, prefix: str = ""):
        entries = children.get(str(parent), [])
        last_idx = len(entries) - 1
        for idx, (rel, is_dir) in enumerate(entries):
            name = rel.name + ("/" if is_dir else "")
            connector = "└── " if idx == last_idx else "├── "
            lines.append(prefix + connector + name)
            if is_dir:
                new_prefix = prefix + ("    " if idx == last_idx else "│   ")
                draw_dir(rel, new_prefix)

    draw_dir(Path(""))
    return "\n".join(lines)


def render_markdown(text: str) -> str:
    """Markdown: コードブロック化"""
    return "```\n" + text + "\n```"


def render_json(items: List[Tuple[Path, bool, int]]) -> str:
    """JSON: ツリーをネストしたオブジェクトに変換"""
    from collections import defaultdict
    nodes: Dict[str, Dict] = {"": {"name": ".", "children": {}}}
    for rel, is_dir, _ in sorted(items, key=lambda x: tuple(x[0].parts)):
        parent = str(Path(*rel.parts[:-1])) if len(rel.parts) > 1 else ""
        name = rel.name + ("/" if is_dir else "")
        parent_node = nodes.setdefault(parent, {"name": parent or ".", "children": {}})
        key = str(rel)
        nodes[key] = {"name": name, "children": {}}
        parent_node["children"][key] = nodes[key]

    def prune(node: Dict) -> Dict:
        if not node["children"]:
            return {"name": node["name"]}
        return {"name": node["name"], "children": [prune(c) for c in node["children"].values()]}

    return json.dumps(prune(nodes[""]), ensure_ascii=False, indent=2)


def render_csv(root: Path, items: List[Tuple[Path, bool, int]]) -> str:
    """CSV: path, is_dir, depth"""
    from io import StringIO
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["path", "is_dir", "depth"])
    base = root.resolve()
    for rel, is_dir, depth in items:
        w.writerow([str(base / rel), 1 if is_dir else 0, depth])
    return buf.getvalue()


def render_dot(items: List[Tuple[Path, bool, int]]) -> str:
    """Graphviz DOT: 親子エッジを生成"""
    lines = ["digraph G {", "  node [shape=box];"]
    for rel, is_dir, _ in items:
        if len(rel.parts) == 1:
            parent = "."
        else:
            parent = str(Path(*rel.parts[:-1]))
        child = str(rel)
        lines.append(f'  "{parent}" -> "{child}";')
    lines.append("}")
    return "\n".join(lines)
