#!/usr/bin/env python3

import cv2
import numpy as np

IMAGE_PATH = "frame.jpg"   # use the image you captured

def main():
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print("ERROR: could not load image", IMAGE_PATH)
        return

    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2

    # small 40x40 patch around the center
    size = 20
    x1 = max(cx - size, 0)
    x2 = min(cx + size, w)
    y1 = max(cy - size, 0)
    y2 = min(cy + size, h)

    patch_bgr = img[y1:y2, x1:x2]
    patch_hsv = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2HSV)

    hsv_vals = patch_hsv.reshape(-1, 3)
    H = hsv_vals[:, 0]
    S = hsv_vals[:, 1]
    V = hsv_vals[:, 2]

    print("Center patch size:", patch_hsv.shape)
    print(f"H (0-179): mean={H.mean():.1f}, min={H.min()}, max={H.max()}")
    print(f"S (0-255): mean={S.mean():.1f}, min={S.min()}, max={S.max()}")
    print(f"V (0-255): mean={V.mean():.1f}, min={V.min()}, max={V.max()}")

if __name__ == "__main__":
    main()
