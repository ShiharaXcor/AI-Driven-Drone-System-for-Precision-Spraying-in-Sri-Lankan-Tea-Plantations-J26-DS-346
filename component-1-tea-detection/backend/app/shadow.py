import cv2
import numpy as np


def shadow_mask(bgr, min_gap=30):
    """Classical baseline: Otsu threshold on LAB lightness, cleaned with morphology.
    Returns (mask 0/255, shadow_ratio). Otsu always finds a split, even on uniform
    images, so if light and dark regions are not clearly different we report no shadow."""
    L = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:, :, 0], (5, 5), 0)
    t, _ = cv2.threshold(L, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark, light = L < t, L >= t
    if dark.sum() == 0 or light.sum() == 0 or (float(L[light].mean()) - float(L[dark].mean())) < min_gap:
        return np.zeros(L.shape, np.uint8), 0.0
    mask = dark.astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)
    return mask, float((mask > 0).mean())


def enhance(bgr, mask, method="clahe", gamma=0.5):
    """Enhance the whole image, then blend it in only inside the (feathered) shadow mask."""
    if method == "gamma":
        lut = np.array([255 * (i / 255.0) ** gamma for i in range(256)], dtype=np.uint8)
        out = cv2.LUT(bgr, lut)
    elif method == "clahe":
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
        out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        return bgr.copy()
    soft = (cv2.GaussianBlur(mask, (31, 31), 0).astype(np.float32) / 255.0)[:, :, None]
    return (out * soft + bgr * (1 - soft)).astype(np.uint8)