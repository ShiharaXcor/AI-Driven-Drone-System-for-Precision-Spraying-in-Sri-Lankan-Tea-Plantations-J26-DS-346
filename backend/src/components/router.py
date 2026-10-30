from fastapi import APIRouter

from src.components.c1_spray_detection.router import router as c1_router
from src.components.c2_wind_handling.router import router as c2_router
from src.components.c3_smart_path.router import router as c3_router
from src.components.c4_maturity.router import router as c4_router

router = APIRouter()
router.include_router(c1_router, prefix="/c1")
router.include_router(c2_router, prefix="/c2")
router.include_router(c3_router, prefix="/c3")
router.include_router(c4_router, prefix="/c4")