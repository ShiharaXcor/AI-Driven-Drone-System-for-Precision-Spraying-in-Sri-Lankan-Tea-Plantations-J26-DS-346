from . import config
from .shadow import shadow_mask

_detector = None
_unet = None


def get_detector():
    global _detector
    if _detector is None:
        from .detector import Detector
        _detector = Detector()
    return _detector


def get_shadow(img):
    """U-Net if its weights exist, otherwise the threshold baseline."""
    global _unet
    if config.SHADOW_MODEL.exists():
        if _unet is None:
            from .shadow_unet import UNetShadow
            _unet = UNetShadow()
        m, r = _unet.mask(img)
        return m, r, "unet"
    m, r = shadow_mask(img)
    return m, r, "threshold"