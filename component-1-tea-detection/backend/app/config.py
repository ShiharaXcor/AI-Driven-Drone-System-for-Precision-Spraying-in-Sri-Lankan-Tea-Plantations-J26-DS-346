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
SAFETY_MODEL = str(_path(os.getenv("SAFETY_MODEL", "models/yolo11n.pt")))
USE_COCO_SAFETY = os.getenv("USE_COCO_SAFETY", "true").lower() == "true"
ENH_METHOD = os.getenv("ENH_METHOD", "clahe")                   # clahe | gamma
SHADOW_MIN_RATIO = float(os.getenv("SHADOW_MIN_RATIO", "0.10"))
MAX_IMAGE_SIDE = int(os.getenv("MAX_IMAGE_SIDE", "1280"))
GPS_LOG_INTERVAL_S = float(os.getenv("GPS_LOG_INTERVAL_S", "0"))     # 0 = background logging off
