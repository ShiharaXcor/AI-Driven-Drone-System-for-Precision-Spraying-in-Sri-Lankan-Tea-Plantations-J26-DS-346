import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]      # component-1-tea-detection/
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./spray.db")
API_KEY = os.getenv("API_KEY", "dev-key")
MODEL_PATH = os.getenv("MODEL_PATH", "models/best.pt")
SHADOW_MODEL = os.getenv("SHADOW_MODEL", "models/shadow_unet.pt")
ENH_METHOD = os.getenv("ENH_METHOD", "clahe")
SHADOW_MIN_RATIO = float(os.getenv("SHADOW_MIN_RATIO", "0.10"))