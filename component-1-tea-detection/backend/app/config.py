import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]      # component-1-tea-detection/
BACKEND_DIR = ROOT / "backend"
load_dotenv(ROOT / ".env")


def _path(value):
    p = Path(value)
    return p if p.is_absolute() else BACKEND_DIR / p


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./spray.db")
API_KEY = os.getenv("API_KEY", "dev-key")
MODEL_PATH = _path(os.getenv("MODEL_PATH", "models/best.pt"))
SHADOW_MODEL = _path(os.getenv("SHADOW_MODEL", "models/shadow_unet.pt"))
SAFETY_MODEL = os.getenv("SAFETY_MODEL", "yolo11n.pt")          # pretrained COCO (person/animal)
USE_COCO_SAFETY = os.getenv("USE_COCO_SAFETY", "true").lower() == "true"
ENH_METHOD = os.getenv("ENH_METHOD", "clahe")                   # clahe | gamma
SHADOW_MIN_RATIO = float(os.getenv("SHADOW_MIN_RATIO", "0.10"))