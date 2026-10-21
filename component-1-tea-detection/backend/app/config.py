import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]      # component-1-tea-detection/
BACKEND_DIR = ROOT / "backend"
load_dotenv(ROOT / ".env")


def _path(value):
    p = Path(value)
    return p if p.is_absolute() else BACKEND_DIR / p


# database and models
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./spray.db")
MODEL_PATH = _path(os.getenv("MODEL_PATH", "models/best.pt"))
SHADOW_MODEL = _path(os.getenv("SHADOW_MODEL", "models/shadow_unet.pt"))
SAFETY_MODEL = str(_path(os.getenv("SAFETY_MODEL", "models/yolo11n.pt")))   # pretrained COCO (person/animal)
USE_COCO_SAFETY = os.getenv("USE_COCO_SAFETY", "true").lower() == "true"

# pipeline
ENH_METHOD = os.getenv("ENH_METHOD", "clahe")                   # clahe | gamma
SHADOW_MIN_RATIO = float(os.getenv("SHADOW_MIN_RATIO", "0.10"))
MAX_IMAGE_SIDE = int(os.getenv("MAX_IMAGE_SIDE", "1280"))
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "15"))

# security
API_KEY = os.getenv("API_KEY", "dev-key")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ADMIN_USER = os.getenv("ADMIN_USER", "operator")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-now")
TOKEN_TTL_S = int(os.getenv("TOKEN_TTL_S", str(8 * 3600)))
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000").split(",") if o.strip()]

# hardware and background jobs
GPS_LOG_INTERVAL_S = float(os.getenv("GPS_LOG_INTERVAL_S", "0"))   # 0 = off
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_INTERVAL_S = float(os.getenv("CAMERA_INTERVAL_S", "1.0"))