"""Creates ONLY the folders and EMPTY files of the Tea Drone System.
No code is written inside any file.

Run from the ROOT of your cloned git repo:   python make_structure.py
- never overwrites an existing file (safe to run twice)
- never touches the .git folder
- frontend/ is NOT created (you will design it later)
"""
from pathlib import Path

ROOT = Path(".")

STANDARD = ["__init__.py", "router.py", "schemas.py", "models.py", "service.py", "constants.py", "exceptions.py"]

COMMON = {
    "auth": [],
    "alerts": [],
    "missions": [],
    "realtime": ["manager.py"],
    "drone": ["telemetry.py", "actuators.py"],
    "spraying": ["coordinator.py"],
}

COMPONENTS = {
    "c1_spray_detection": {
        "tea_detection": ["detector.py", "pipeline.py", "kml.py"],
        "shadow": ["shadow.py"],
        "safety_decision": ["decision.py"],
    },
    "c2_wind_handling": {
        "wind_prediction": ["predictor.py"],
        "compensation": ["compensation.py"],
    },
    "c3_smart_path": {
        "energy_model": ["energy_model.py"],
        "path_agent": ["state_builder.py", "agent.py"],
        "path_safety": ["safety_layer.py"],
    },
    "c4_maturity": {
        "maturity_classification": ["classifier.py"],
        "quality_rules": ["quality.py", "rules.py"],
        "prescription": ["prescription.py"],
    },
}

ML_COMPONENTS = ["c1-spray-detection", "c2-wind-handling", "c3-smart-path", "c4-maturity"]
ML_SUBFOLDERS = ["training", "notebooks", "configs", "reports", "data", "artifacts"]

# other empty files (path relative to the repo root)
EMPTY_FILES = [
    "backend/src/main.py", "backend/src/config.py", "backend/src/database.py",
    "backend/src/dependencies.py", "backend/src/exceptions.py",
    "backend/src/components/router.py",
    "backend/tests/conftest.py", "backend/tests/test_health.py",
    "backend/requirements.txt", "backend/Dockerfile", "backend/.dockerignore", "backend/.env.example",
    "mlops/README.md", "mlops/evaluation/thresholds.yaml", "mlops/evaluation/evaluate_gate.py",
    "mlops/registry/models.yaml",
    ".github/workflows/ci-backend.yml", ".github/workflows/ml-gate.yml", ".github/workflows/docker-publish.yml",
    "docker-compose.yml", ".env.example", ".gitignore", "README.md",
    "docs/api-contracts/README.md", "docs/architecture/README.md",
    "edge/README.md", "simulation/README.md",
]

# folders that stay empty (a .gitkeep is added so git keeps them)
EMPTY_DIRS = [
    "backend/alembic/versions", "backend/static",
    "mlops/model_cards",
    "simulation/gazebo/worlds", "simulation/gazebo/models", "simulation/ardupilot",
    "edge/camera", "edge/gps", "edge/actuators", "edge/mavlink", "edge/services",
    "docs/diagrams", "docs/reports",
    "scripts",
]


def touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def make_domain(base: Path, name: str, extra: list):
    for f in STANDARD + extra:
        touch(base / name / f)


def make():
    src = ROOT / "backend" / "src"
    tests = ROOT / "backend" / "tests"

    touch(src / "__init__.py")
    touch(tests / "__init__.py")

    # common
    touch(src / "common" / "__init__.py")
    touch(tests / "common" / "__init__.py")
    for name, extra in COMMON.items():
        make_domain(src / "common", name, extra)
        touch(tests / "common" / name / "__init__.py")
        touch(tests / "common" / name / f"test_{name}.py")

    # components
    touch(src / "components" / "__init__.py")
    touch(tests / "components" / "__init__.py")
    for comp, domains in COMPONENTS.items():
        touch(src / "components" / comp / "__init__.py")
        touch(src / "components" / comp / "router.py")
        touch(tests / "components" / comp / "__init__.py")
        for name, extra in domains.items():
            make_domain(src / "components" / comp, name, extra)
            touch(tests / "components" / comp / name / "__init__.py")
            touch(tests / "components" / comp / name / f"test_{name}.py")

    # ml
    for comp in ML_COMPONENTS:
        touch(ROOT / "ml" / comp / "README.md")
        for sub in ML_SUBFOLDERS:
            (ROOT / "ml" / comp / sub).mkdir(parents=True, exist_ok=True)

    for rel in EMPTY_FILES:
        touch(ROOT / rel)
    for rel in EMPTY_DIRS:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    # git does not store empty folders, so add .gitkeep to them
    for d in sorted(ROOT.rglob("*")):
        if ".git" in d.parts or ".venv" in d.parts:
            continue
        if d.is_dir() and not any(d.iterdir()):
            (d / ".gitkeep").touch()

    folders = sum(1 for p in ROOT.rglob("*") if p.is_dir() and ".git" not in p.parts)
    files = sum(1 for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts)
    print(f"Done: {folders} folders, {files} files (all empty). frontend/ was NOT created.")


if __name__ == "__main__":
    if not Path(".git").exists():
        if input("No .git folder here. Create the structure anyway? (y/N) ").strip().lower() != "y":
            raise SystemExit("Stopped. Run this from the root of your cloned repo.")
    make()