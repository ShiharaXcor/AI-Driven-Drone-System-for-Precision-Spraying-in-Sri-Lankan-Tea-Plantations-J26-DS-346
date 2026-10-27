"""Adds the component and page folders inside frontend/src.
Run from the ROOT of the repo AFTER creating the Vite app:  python make_frontend.py
Only folders are created (a .gitkeep keeps each empty folder in git).
"""
from pathlib import Path

SRC = Path("frontend") / "src"
NAMES = ["detection", "wind", "path", "maturity"]

if not (Path("frontend") / "package.json").exists():
    raise SystemExit("frontend/package.json not found. Create the Vite app first (see step 1).")

for parent in ("components", "pages"):
    for name in NAMES:
        folder = SRC / parent / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".gitkeep").touch()

print("Created:")
for parent in ("components", "pages"):
    for name in NAMES:
        print(f"  frontend/src/{parent}/{name}")