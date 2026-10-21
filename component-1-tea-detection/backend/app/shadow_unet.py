import cv2
import numpy as np
import torch
import segmentation_models_pytorch as smp
from . import config

SIZE = 384
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


class UNetShadow:
    def __init__(self):
        self.model = smp.Unet("resnet18", encoder_weights=None, in_channels=3, classes=1)
        self.model.load_state_dict(torch.load(str(config.SHADOW_MODEL), map_location="cpu"))
        self.model.eval()

    @torch.no_grad()
    def mask(self, bgr):
        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(cv2.resize(bgr, (SIZE, SIZE)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        x = torch.from_numpy(((rgb - MEAN) / STD).transpose(2, 0, 1))[None]
        p = torch.sigmoid(self.model(x))[0, 0].numpy()
        m = cv2.resize((p > 0.5).astype(np.uint8) * 255, (w, h), interpolation=cv2.INTER_NEAREST)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)
        return m, float((m > 0).mean())