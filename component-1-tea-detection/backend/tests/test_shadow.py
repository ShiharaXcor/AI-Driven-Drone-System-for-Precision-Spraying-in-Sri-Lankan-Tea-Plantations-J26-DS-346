import numpy as np
from app.shadow import shadow_mask, enhance


def test_no_shadow_on_uniform_image():
    img = np.full((200, 200, 3), 120, np.uint8)
    assert shadow_mask(img)[1] == 0.0


def test_shadow_found_and_brightened():
    img = np.full((200, 200, 3), 200, np.uint8)
    img[:, :100] = 40                                    # dark half = artificial shadow
    mask, ratio = shadow_mask(img)
    assert 0.3 < ratio < 0.7
    assert enhance(img, mask, "gamma")[:, :80].mean() > img[:, :80].mean()
    assert enhance(img, mask, "clahe")[:, :80].mean() > img[:, :80].mean()


def test_enhancement_leaves_bright_area_unchanged():
    img = np.full((200, 200, 3), 200, np.uint8)
    img[:, :100] = 40
    mask, _ = shadow_mask(img)
    out = enhance(img, mask, "gamma")
    assert abs(float(out[:, 150:].mean()) - float(img[:, 150:].mean())) < 3


def test_unknown_method_returns_copy():
    img = np.full((50, 50, 3), 100, np.uint8)
    assert (enhance(img, np.zeros((50, 50), np.uint8), "none") == img).all()