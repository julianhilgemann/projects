# tree_yaml.py
from pathlib import Path
import sys

EXCLUDES = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}

def print_tree_yaml(path: Path, depth=0, max_depth=999):
    if depth == 0:
        print(f"{path.name}/")
    if depth >= max_depth:
        return
    # dirs first, then files; case-insensitive sort on Windows
    dirs  = sorted([p for p in path.iterdir() if p.is_dir() and p.name not in EXCLUDES], key=lambda p: p.name.lower())
    files = sorted([p for p in path.iterdir() if p.is_file() and p.name not in EXCLUDES], key=lambda p: p.name.lower())

    indent = "  " * (depth + 1)
    for d in dirs:
        print(f"{indent}- {d.name}/")
        print_tree_yaml(d, depth + 1, max_depth)
    for f in files:
        print(f"{indent}- {f.name}")

if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print_tree_yaml(root.resolve())